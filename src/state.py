# src/state.py

from typing import Annotated, Any
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    Define el estado de nuestro flujo de orquestación.

    NOTA: El uso de Annotated con add_messages es crucial para que LangGraph maneje correctamente el historial de mensajes.
    """
    messages: Annotated[list[BaseMessage], add_messages]
    message_id: str
    original_notification: Any