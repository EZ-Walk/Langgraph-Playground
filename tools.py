from langchain_community.tools.tavily_search import TavilySearchResults
import json

from langchain_core.messages import ToolMessage

tool = TavilySearchResults(max_results=2)
tools = [tool]
# tool.invoke("What's a 'node' in LangGraph?")

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

tool_node = BasicToolNode(tools=tools)
            
            