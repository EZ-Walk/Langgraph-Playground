from langchain_community.tools.tavily_search import TavilySearchResults
import json

from langchain_core.messages import ToolMessage

from langgraph.prebuilt import ToolNode, tools_condition

import dotenv

from typing import Optional

dotenv.load_dotenv()

tool = TavilySearchResults(max_results=2)
tools = [tool]

class BasicToolNode:
    """A node that runs the tools requested in the last AI message."""
    
    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}
        
    def __call__(self, inputs:dict):
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No messages found in inputs")
        
        outputs = []
        for tool_call in message.tool_calls:
            tool_result = self.tools_by_name[tool_call.tool_name].invoke(tool_call['args'])
            outputs.append(ToolMessage(
                content=json.dumps(tool_result),
                name=tool_call['name'],
                tool_call_id=tool_call['id'],
            ))
            
        return {"messages": outputs}

# tool_node = BasicToolNode(tools=tools)
tool_node = ToolNode(tools=tools)

def fetch_comment_from_parent(comments: dict, parent_id: str, comment_id: Optional[str] = None):
    """
    Sort comments returned by the notion API by returning a list of ordered comments belonging to the block with the given parent_id.
    Optionally, return only the comment requested by ID.
    
    Args:
        comments (dict): Dictionary of comments retrieved from Notion
        parent_id (str): ID of the parent block
        comment_id (str, optional): ID of the specific comment to fetch
        
    Returns:
        dict: Dictionary of comments or a specific comment if comment_id is provided
    """
 
    # catch no comments found by checking the length of the results field
    if len(comments.get('results', [])) == 0:
        return {}

    # optionally, return only the comment requested by ID
    if comment_id:
        for this_c in comments.get('results'):
            if this_c['id'] == comment_id:
                return this_c

    # Finally, return all comments
    return comments.get('results', 'No comments found')