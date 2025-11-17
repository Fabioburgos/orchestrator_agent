# src/graph.py

import json
from .state import AgentState
from custom_logging import get_logger
from .tool_loader import initialize_tool_system, call_mcp_tool
from langgraph.graph import StateGraph, END
from core.llm_client import get_tool_bound_llm
from langchain_core.messages import ToolMessage, AIMessage

logger = get_logger(__name__)

# 🔥 Inicializar sistema de herramientas MCP (carga todas las herramientas y mapeo)
logger.info("Inicializando sistema de herramientas MCP...")
tools = initialize_tool_system()

if not tools:
    logger.error("⚠️ NO SE CARGARON HERRAMIENTAS MCP")
else:
    logger.info(f"✅ Herramientas disponibles: {[t.name for t in tools]}")
    for tool in tools:
        logger.info(f"   - {tool.name}: {tool.description[:100]}...")
        # 🔥 MOSTRAR EL SCHEMA COMPLETO DE CADA HERRAMIENTA
        logger.info(f"   - Schema de {tool.name}:")
        logger.info(f"     args_schema: {tool.args_schema}")
        if tool.args_schema:
            schema_dict = tool.args_schema.model_json_schema()
            logger.info(f"     JSON Schema:")
            logger.info(json.dumps(schema_dict, indent=6))

# Obtener modelo LLM configurado con las herramientas
model = get_tool_bound_llm(tools)


async def agent_node(state: AgentState):
    """
    Nodo del agente: invoca el LLM para decidir el siguiente paso.
    """
    messages = state["messages"]

    # Filtrar mensajes para evitar ToolMessage sin tool_calls previos
    filtered_messages = []
    has_tool_calls = False

    for msg in messages:
        if isinstance(msg, ToolMessage):
            if has_tool_calls:
                filtered_messages.append(msg)
        else:
            filtered_messages.append(msg)
            has_tool_calls = hasattr(msg, 'tool_calls') and len(msg.tool_calls) > 0

    # Invocar el LLM
    logger.debug(f"Invocando LLM con {len(filtered_messages)} mensajes")
    response = await model.ainvoke(filtered_messages)

    # Log de decisión con validación
    if hasattr(response, 'tool_calls') and response.tool_calls:
        available_tool_names = [t.name for t in tools]
        
        for tool_call in response.tool_calls:
            tool_name = tool_call.get('name', 'unknown')
            logger.info(f"LLM decidió ejecutar: {tool_name}")
            
            # 🔥 VALIDACIÓN: Advertir si intenta invocar herramienta inexistente
            if tool_name not in available_tool_names:
                logger.error(f"❌ LLM ALUCINÓ - Herramienta '{tool_name}' NO EXISTE")
                logger.error(f"   Herramientas válidas: {available_tool_names}")
                logger.error(f"   Esto indica un problema con el prompt")
    else:
        logger.info("LLM finalizó sin invocar herramientas")

    return {"messages": [response]}


async def tool_node(state: AgentState):
    """
    Nodo de herramientas: ejecuta herramientas MCP via Lambda.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
        logger.warning("tool_node invocado sin tool_calls en el mensaje")
        return state
    
    tool_results = []
    available_tool_names = [t.name for t in tools]
    
    for tool_call in last_message.tool_calls:
        tool_name = tool_call.get('name')
        tool_input = tool_call.get('input', {})
        tool_id = tool_call.get('id')

        # 🔥 LOGGING DETALLADO DEL TOOL_CALL
        logger.info("="*80)
        logger.info(f"[TOOL_NODE] 🔍 PROCESANDO TOOL_CALL")
        logger.info("="*80)
        logger.info(f"[TOOL_NODE] Tool name: {tool_name}")
        logger.info(f"[TOOL_NODE] Tool ID: {tool_id}")
        logger.info(f"[TOOL_NODE] Type of tool_input: {type(tool_input)}")
        logger.info(f"[TOOL_NODE] Tool input keys: {list(tool_input.keys()) if isinstance(tool_input, dict) else 'N/A'}")
        logger.info(f"[TOOL_NODE] Tool input completo: {json.dumps(tool_input, indent=2, default=str)}")

        # 🔥 VALIDACIÓN Y CORRECCIÓN: Verificar message_id en tool_input
        if isinstance(tool_input, dict):
            if 'message_id' in tool_input and tool_input['message_id']:
                logger.info(f"[TOOL_NODE] ✅ message_id en tool_input: {tool_input['message_id'][:50]}...")
            else:
                logger.error(f"[TOOL_NODE] ❌ message_id AUSENTE en tool_input!")
                logger.error(f"[TOOL_NODE] Esto significa que el LLM no lo incluyó en su invocación")

                # 🔥 WORKAROUND: Inyectar el message_id desde el state si está disponible
                if 'message_id' in state and state['message_id']:
                    logger.info(f"[TOOL_NODE] 🔧 APLICANDO WORKAROUND: Inyectando message_id desde el state")
                    logger.info(f"[TOOL_NODE] message_id del state: {state['message_id'][:50]}...")
                    tool_input['message_id'] = state['message_id']
                    logger.info(f"[TOOL_NODE] ✅ message_id inyectado exitosamente")
                else:
                    logger.error(f"[TOOL_NODE] ❌ No se puede aplicar workaround: message_id tampoco está en el state")
        logger.info("="*80)

        # 🔥 VALIDACIÓN CRÍTICA: Rechazar herramientas inexistentes
        if tool_name not in available_tool_names:
            logger.error(f"❌ Rechazando invocación de herramienta inexistente: {tool_name}")
            result = (
                f"ERROR: La herramienta '{tool_name}' no existe.\n\n"
                f"Herramientas disponibles: {', '.join(available_tool_names)}\n\n"
                f"⚠️ Por favor, usa solo las herramientas que existen."
            )
        else:
            logger.info(f"Ejecutando herramienta: {tool_name}")
            
            try:
                result = await call_mcp_tool(tool_name, tool_input)
                result_preview = result[:200] if len(result) > 200 else result
                logger.info(f"✓ Herramienta ejecutada correctamente")
                logger.debug(f"Resultado: {result_preview}...")
                
            except Exception as e:
                logger.error(f"❌ Error ejecutando {tool_name}: {e}", exc_info=True)
                result = f"Error ejecutando herramienta {tool_name}: {str(e)}"
        
        # Crear mensaje de resultado
        tool_message = ToolMessage(
            content=result,
            tool_call_id=tool_id,
            name=tool_name
        )
        tool_results.append(tool_message)
    
    logger.debug(f"Retornando {len(tool_results)} resultados de herramientas")
    return {"messages": tool_results}


def should_continue(state: AgentState):
    """
    Decide si continuar con herramientas o terminar el flujo.
    """
    last_message = state["messages"][-1]
    
    if isinstance(last_message, AIMessage):
        if hasattr(last_message, 'tool_calls') and len(last_message.tool_calls) > 0:
            logger.debug("Continuando con nodo de herramientas")
            return "continue_to_tools"
    
    logger.debug("Finalizando flujo")
    return "end"


def build_graph():
    """
    Construye y compila el grafo de orquestación LangGraph.
    """
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    
    workflow.set_entry_point("agent")
    
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue_to_tools": "tools",
            "end": END
        }
    )
    
    workflow.add_edge("tools", "agent")
    
    app = workflow.compile()
    logger.info("✅ Grafo LangGraph compilado exitosamente")
    
    return app