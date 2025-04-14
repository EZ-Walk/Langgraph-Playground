
import dotenv
import json
import os
from flask import Flask, request, jsonify

dotenv.load_dotenv()
from typing import Annotated

from langchain_anthropic import ChatAnthropic
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
from typing_extensions import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, interrupt

from notion_client import Client

from tools import fetch_comment_from_parent


class State(TypedDict):
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)


@tool
def human_assistance(query: str) -> str:
    """Request assistance from a human."""
    human_response = interrupt({"query": query})
    return human_response["data"]


tool = TavilySearchResults(max_results=2)
tools = [tool, human_assistance]
llm = ChatAnthropic(model="claude-3-5-sonnet-20240620")
llm_with_tools = llm.bind_tools(tools)


def chatbot(state: State):
    message = llm_with_tools.invoke(state["messages"])
    assert(len(message.tool_calls) <= 1)
    return {"messages": [message]}


graph_builder.add_node("chatbot", chatbot)

tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)

graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")

memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)

def stream_graph_updates(user_input: str, config: dict):
    for event in graph.stream(
        {"messages": [{"role": "user", "content": user_input}]},
        config=config,
        stream_mode="values"
    ):
        print(event)
        notion_client.comments.create(
            discussion_id=config['configurable']['thread_id'],
            rich_text=[{
                "type": "text",
                "text": {
                    "content": event["messages"][-1].content
                }
            }]
        )
            

def handle_comment(payload: dict):
    # Find the discussion ID of the comment that just came in.
    comments = notion_client.comments.list(block_id=payload['data']['parent']['id'])
    
    this_comment = fetch_comment_from_parent(
        comments=comments,
        parent_id=payload['data']['parent']['id'],
        comment_id=payload['entity']['id']
    )
    
    discussion_id = this_comment['discussion_id']
    
    if payload['type'] == 'comment.created':
        print(f"New comment: {this_comment}")
        
        response = graph.invoke(
            {"messages": [
                {"role": "user", "content": this_comment['rich_text'][0]['plain_text']}
            ]},
            config={"configurable": {"thread_id": discussion_id}}
        )
        
        notion_client.comments.create(
            discussion_id=discussion_id,
            rich_text=[{
                "type": "text",
                "text": {
                    "content": response["messages"][-1].content
                }
            }]
        )
    
    elif payload['type'] == 'comment.deleted':
        print(f"Comment deleted: {this_comment}")
    
    elif payload['type'] == 'comment.updated':
        print(f"Comment updated: {this_comment}")
        
    return
    
    # Comment.created
    # create a 

# Initialize Flask app
app = Flask(__name__)

@app.route('/', methods=['GET'])
def status():
    # get the state history of the graph
    return jsonify({"status": "ok", "message": "LangGraph webhook server is running"})

@app.route('/events', methods=['POST'])
def webhook_handler():
    try:
        payload = request.json
        print(f"Received webhook payload: {json.dumps(payload, indent=2)}")

        if payload['type'].startswith('comment'):
            if payload['authors'][0]['type'] == 'person':
                handle_comment(payload)
                return jsonify({"status": "success", "message": "Comment processed"}), 200
            else:
                return jsonify({"status": "success", "message": "Bot response posted"}), 200

        
        return jsonify({"status": "success", "message": "Webhook received"}), 200
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Keep the original CLI functionality for testing
if __name__ == "__main__":
    import sys
    
    # Check if we should run in server mode
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        print("Starting Flask server...")
        notion_client = Client(auth=os.getenv("NOTION_API_KEY"))
        app.run(host='0.0.0.0', port=5001, debug=True)
    else:
        # Original CLI mode
        print("Running in CLI mode. Use 'python main.py server' to start the Flask server.")
        while True:
            try:
                user_input = input("User: ")
                if user_input.lower() in ["quit", "exit", "q"]:
                    print("Goodbye!")
                    break
                stream_graph_updates(user_input)
            except Exception as e:
                print(f"Error: {str(e)}")
                break