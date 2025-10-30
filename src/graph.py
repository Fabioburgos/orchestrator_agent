# src/graph.py

import os
from .state import AgentState
from .tool_loader import load_mcp_tools
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, END
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import ToolMessage

tools = load_mcp_tools()
tool_node = ToolNode(tools)

model = AzureChatOpenAI(
    api_key = os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version = os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    temperature = 0
).bind_tools(tools)

async def agent_node(state: AgentState):
    """
    Llama al LLM (de forma asíncrona) para que decida el siguiente paso.
    """
    messages = state["messages"]
    
    # (mensajes tool sin un tool_call previo)
    filtered_messages = []
    has_tool_calls = False
    
    for msg in messages:
        if isinstance(msg, ToolMessage):
            # Solo añadir ToolMessage si hubo un tool_call antes
            if has_tool_calls:
                filtered_messages.append(msg)
        else:
            filtered_messages.append(msg)
            # Verificar si este mensaje tiene tool_calls
            has_tool_calls = hasattr(msg, 'tool_calls') and len(msg.tool_calls) > 0
    
    response = await model.ainvoke(filtered_messages)
    return {"messages": [response]}

def should_continue(state: AgentState):
    """
    Decide si el flujo termina o si debe llamar a una herramienta.
    """
    last_message = state["messages"][-1]
    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
        return "end"
    return "continue_to_tools"

def build_graph():
    """
    Construye y compila el grafo de LangGraph.
    """
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {"continue_to_tools": "tools", "end": END}
    )
    workflow.add_edge("tools", "agent")
    return workflow.compile()