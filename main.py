
import dotenv
import json
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

def stream_graph_updates(user_input: str):
    for event in graph.stream(
        {"messages": [{"role": "user", "content": user_input}]},
        config={"configurable": {"thread_id": "1"}},
        
    ):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)

# Initialize Flask app
app = Flask(__name__)

@app.route('/', methods=['GET'])
def status():
    return jsonify({"status": "ok", "message": "LangGraph webhook server is running"})

@app.route('/events', methods=['POST'])
def webhook_handler():
    try:
        payload = request.json
        print(f"Received webhook payload: {json.dumps(payload, indent=2)}")
        
        # Here you can process the webhook payload and potentially use the LangGraph agent
        # For example, if the payload contains a message, you could pass it to the agent:
        # if 'message' in payload:
        #     stream_graph_updates(payload['message'])
        
        return jsonify({"status": "success", "message": "Webhook received"})
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Keep the original CLI functionality for testing
if __name__ == "__main__":
    import sys
    
    # Check if we should run in server mode
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        print("Starting Flask server...")
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