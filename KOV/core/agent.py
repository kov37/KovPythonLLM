"""
Core agent functionality for KOV using LangGraph.
"""

import logging
from typing import Literal
from langchain_ollama import ChatOllama
from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, BaseMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from KOV.tools.operations import read_file, write_file, list_dir, delete_file, run_shell, fetch_url, download_file


# Define tools using @tool decorator
@tool
def read_file_tool(path: str) -> str:
    """Read the contents of a file."""
    return read_file(path)

@tool  
def write_file_tool(path: str, content: str) -> str:
    """Write content to a file."""
    return write_file({"path": path, "content": content})

@tool
def list_directory_tool(path: str = ".") -> str:
    """List files in a directory."""
    return list_dir(path)

@tool
def delete_file_tool(path: str) -> str:
    """Delete a file."""
    return delete_file(path)

@tool
def run_shell_tool(command: str) -> str:
    """Execute a shell command."""
    return run_shell(command)

@tool
def fetch_url_tool(url: str) -> str:
    """Fetch content from a URL or website."""
    return fetch_url(url)

@tool
def download_file_tool(url: str, filename: str) -> str:
    """Download a file from the internet."""
    return download_file(url, filename)


class KOVAgent:
    """KOV AI Developer Agent with file system and shell access using LangGraph."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.llm = ChatOllama(model="llama3.2:3b", temperature=0.1)
        self.tools = [read_file_tool, write_file_tool, list_directory_tool, delete_file_tool, run_shell_tool, fetch_url_tool, download_file_tool]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.agent = self._create_agent()
        
    def _create_agent(self):
        """Create and configure the KOV agent using LangGraph."""
        
        def llm_call(state: MessagesState):
            """LLM decides whether to call a tool or not."""
            messages = state["messages"]
            response = self.llm_with_tools.invoke(messages)
            return {"messages": [response]}
        
        def should_continue(state: MessagesState) -> Literal["tools", END]:
            """Decide if we should continue or stop based on tool calls."""
            messages = state["messages"]
            last_message = messages[-1]
            
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            return END
        
        # Create the graph
        workflow = StateGraph(MessagesState)
        
        # Add nodes
        workflow.add_node("agent", llm_call)
        workflow.add_node("tools", ToolNode(self.tools))
        
        # Add edges
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
    
    def run(self, user_input: str) -> str:
        """Process user input and return agent response."""
        system_message = SystemMessage(content="""You are KOV, a helpful AI assistant with access to file system, shell, and internet tools. 

Have natural conversations with users. When they mention files, directories, want to run commands, or need internet access, automatically use your tools to help them. Don't ask permission - just do what makes sense.

Examples:
- If they say "what files are here?" → use list_directory_tool
- If they say "show me that config file" → use read_file_tool  
- If they say "create a readme" → use write_file_tool
- If they say "what's my username?" → use run_shell_tool with 'whoami'
- If they say "check what's on google.com" → use fetch_url_tool
- If they say "download this file" → use download_file_tool

Be conversational and helpful. Use tools naturally as part of your responses.""")
        
        human_message = HumanMessage(content=user_input)
        
        try:
            result = self.agent.invoke({"messages": [system_message, human_message]})
            
            # Extract the final response
            messages = result["messages"]
            final_message = messages[-1]
            
            if hasattr(final_message, 'content'):
                return final_message.content
            else:
                return str(final_message)
                
        except Exception as e:
            if self.debug:
                logging.error(f"Agent error: {str(e)}")
            return f"Error: {str(e)}"
