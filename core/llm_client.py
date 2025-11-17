# core/llm_client.py

from pathlib import Path
from typing import List, Dict, Any
from config.settings import settings
from custom_logging import get_logger
from langchain_core.tools import BaseTool
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

logger = get_logger(__name__)

# --- 1. CONFIGURACIÓN Y CARGA DE PROMPTS ---

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

def load_prompt_template(file_name: str) -> ChatPromptTemplate:
    """
    Carga una plantilla de prompt desde un archivo .txt en el directorio /prompts.
    """
    prompt_path = PROMPTS_DIR / file_name
    if not prompt_path.exists():
        raise FileNotFoundError(f"El fichero de prompt no se encontró en: {prompt_path}")

    template_string = prompt_path.read_text(encoding = "utf-8")
    return ChatPromptTemplate.from_template(template_string)

# --- 2. CONFIGURACIÓN DEL CLIENTE LLM (SINGLETON) ---

# Se crea una única vez cuando el módulo se importa.
_client = AzureChatOpenAI(
    azure_deployment = settings.AZURE_OPENAI_DEPLOYMENT_NAME,
    api_version = settings.AZURE_OPENAI_API_VERSION,
    azure_endpoint = settings.AZURE_OPENAI_ENDPOINT,
    api_key = settings.AZURE_OPENAI_API_KEY,
    temperature = 0.1,
)

# --- 3. FUNCIONES EXPUESTAS PARA EL RESTO DE LA APLICACIÓN ---

def get_tool_bound_llm(tools: List[BaseTool]) -> AzureChatOpenAI:
    """
    Toma el cliente LLM base y lo enlaza a un conjunto específico de herramientas.
    Esta es la función que usará nuestro agente de LangGraph.
    """
    return _client.bind_tools(tools)

async def invoke_llm_with_prompt(prompt_template: ChatPromptTemplate, context: Dict[str, Any]) -> str:
    """
    Función genérica para invocar el LLM con un prompt y un contexto.
    (Útil para futuras necesidades que no involucren herramientas).
    """
    prompt = prompt_template.format_messages(**context)
    try:
        response: AIMessage = await _client.ainvoke(prompt)
        return response.content
    except Exception as e:
        logger.exception(f"Error en la llamada al LLM: {e}")
        raise