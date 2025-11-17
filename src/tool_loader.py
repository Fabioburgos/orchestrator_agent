# src/tool_loader.py

import json
import boto3
import asyncio
import logging
from typing import List, Dict, Any
from config.settings import settings
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# 🔥 Cliente Lambda con región configurable
lambda_client = boto3.client('lambda', region_name=settings.AWS_REGION)


class MCPToolMetadata:
    """Metadata de herramienta MCP para tracking interno"""
    def __init__(self, name: str, description: str, input_schema: Dict, wrapper_source: str):
        self.name = name
        self.description = description
        self.inputSchema = input_schema
        self.wrapper_source = wrapper_source


async def invoke_wrapper_lambda(lambda_function_name: str, method: str, params: Dict = None) -> Dict:
    """
    Invoca un wrapper MCP Lambda con JSON-RPC.
    
    Args:
        lambda_function_name: Nombre de la función Lambda del wrapper
        method: "tools/list" o "tools/call"
        params: Parámetros del método
    
    Returns:
        Respuesta JSON-RPC del wrapper
    """
    
    payload = {
        "method": method,
        "params": params or {}
    }
    
    logger.info(f"[MCP] Invocando wrapper: {lambda_function_name}")
    logger.info(f"[MCP] Método: {method}")
    logger.debug(f"[MCP] Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = lambda_client.invoke(
            FunctionName=lambda_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        response_payload = json.loads(response['Payload'].read())
        logger.debug(f"[MCP] Response: {json.dumps(response_payload, indent=2)}")
        
        return response_payload
        
    except Exception as e:
        logger.error(f"[MCP] Error invocando {lambda_function_name}: {e}", exc_info=True)
        raise


async def get_mcp_tools_from_wrapper(wrapper_name: str, lambda_function_name: str) -> List[StructuredTool]:
    """
    Obtiene herramientas de un wrapper MCP específico.
    
    Args:
        wrapper_name: Nombre lógico del wrapper (para logging)
        lambda_function_name: Nombre de la función Lambda
    
    Returns:
        Lista de herramientas LangChain del wrapper
    """
    logger.info(f"[MCP] Cargando herramientas desde wrapper: {wrapper_name}")
    
    try:
        response = await invoke_wrapper_lambda(lambda_function_name, "tools/list")
        
        # Validar respuesta
        if "error" in response:
            logger.error(f"[MCP] Error en {wrapper_name}: {json.dumps(response['error'])}")
            return []
        
        # Extraer herramientas
        result = response.get("result", {})
        tools_data = result.get("tools", [])
        
        if not tools_data:
            logger.warning(f"[MCP] {wrapper_name} no retornó herramientas")
            return []
        
        logger.info(f"[MCP] ✅ {len(tools_data)} herramienta(s) desde {wrapper_name}")
        
        # Convertir a herramientas LangChain
        langchain_tools = []
        for tool_data in tools_data:
            tool_name = tool_data["name"]
            
            # Crear metadata
            metadata = MCPToolMetadata(
                name=tool_name,
                description=tool_data["description"],
                input_schema=tool_data["inputSchema"],
                wrapper_source=lambda_function_name
            )
            
            # Guardar metadata para routing
            _tool_metadata_map[tool_name] = metadata
            
            # Crear modelo Pydantic dinámicamente desde el schema
            input_schema = tool_data["inputSchema"]
            properties = input_schema.get("properties", {})
            required = input_schema.get("required", [])

            # 🔥 CREAR CLASE PYDANTIC CORRECTAMENTE
            logger.info(f"[MCP] Construyendo modelo Pydantic para {tool_name}")
            logger.info(f"[MCP] Properties: {list(properties.keys())}")
            logger.info(f"[MCP] Required: {required}")

            # Crear anotaciones y valores de campo separadamente
            annotations = {}
            field_definitions = {}

            for prop_name, prop_schema in properties.items():
                # Determinar tipo (por ahora todo es str, podrías mapear tipos JSON aquí)
                field_type = str
                field_desc = prop_schema.get("description", "")
                is_required = prop_name in required

                # Agregar a anotaciones
                annotations[prop_name] = field_type

                # Crear Field con configuración correcta
                if is_required:
                    field_definitions[prop_name] = Field(..., description=field_desc)
                    logger.info(f"[MCP]   - {prop_name}: {field_type.__name__} (required)")
                else:
                    field_definitions[prop_name] = Field(default=None, description=field_desc)
                    logger.info(f"[MCP]   - {prop_name}: {field_type.__name__} (optional)")

            # Crear el modelo dinámicamente con la estructura correcta
            InputModel = type(
                f"{tool_name}_Input",
                (BaseModel,),
                {
                    "__annotations__": annotations,
                    **field_definitions
                }
            )

            # 🔥 VALIDAR Y MOSTRAR EL SCHEMA JSON GENERADO
            generated_schema = InputModel.model_json_schema()
            logger.info(f"[MCP] ✅ Modelo Pydantic creado: {InputModel.__name__}")
            logger.info(f"[MCP] Schema JSON generado para {tool_name}:")
            logger.info(json.dumps(generated_schema, indent=2))

            # 🔥 VALIDACIÓN CRÍTICA: Verificar que message_id esté en required
            schema_required = generated_schema.get("required", [])
            if "message_id" in required and "message_id" not in schema_required:
                logger.error(f"[MCP] ❌ PROBLEMA: message_id debería estar en required pero no está!")
                logger.error(f"[MCP]    Original required: {required}")
                logger.error(f"[MCP]    Schema required: {schema_required}")
            else:
                logger.info(f"[MCP] ✅ Campo 'message_id' correctamente configurado como required")

            # Crear función wrapper que capture el tool_name correcto
            def make_tool_func(captured_tool_name):
                async def tool_func(**kwargs):
                    """Función que ejecuta la herramienta MCP"""
                    logger.info("="*80)
                    logger.info(f"[TOOL_FUNC] 🔥 EJECUTANDO TOOL_FUNC")
                    logger.info("="*80)
                    logger.info(f"[TOOL_FUNC] Tool name: {captured_tool_name}")
                    logger.info(f"[TOOL_FUNC] Type of kwargs: {type(kwargs)}")
                    logger.info(f"[TOOL_FUNC] kwargs keys: {list(kwargs.keys())}")
                    logger.info(f"[TOOL_FUNC] kwargs completo: {json.dumps(kwargs, default=str, indent=2)}")

                    # 🔥 VALIDACIÓN CRÍTICA: Verificar que message_id existe
                    if 'message_id' in kwargs:
                        logger.info(f"[TOOL_FUNC] ✅ message_id encontrado: {kwargs['message_id'][:50]}...")
                    else:
                        logger.error(f"[TOOL_FUNC] ❌ message_id NO ENCONTRADO en kwargs!")
                        logger.error(f"[TOOL_FUNC] Esto indica un problema en la construcción del modelo Pydantic")

                    logger.info("="*80)

                    result = await call_mcp_tool(captured_tool_name, kwargs)
                    logger.info(f"[TOOL_FUNC] Resultado de call_mcp_tool: {result[:200] if result else 'None'}...")
                    return result
                return tool_func
            
            tool_func = make_tool_func(tool_name)
            
            # Actualizar metadata de la función
            tool_func.__name__ = tool_name
            tool_func.__doc__ = tool_data["description"]
            
            # Crear StructuredTool de LangChain
            langchain_tool = StructuredTool(
                name=tool_name,
                description=tool_data["description"],
                func=tool_func,
                coroutine=tool_func,  # Para soporte async
                args_schema=InputModel
            )
            
            langchain_tools.append(langchain_tool)
            
            logger.info(f"[MCP]   ✓ {tool_name} (desde {wrapper_name})")
            logger.debug(f"[MCP]     Descripción: {tool_data['description'][:100]}...")
        
        return langchain_tools
        
    except Exception as e:
        logger.error(f"[MCP] Error obteniendo herramientas de {wrapper_name}: {e}", exc_info=True)
        return []


async def get_all_mcp_tools() -> List[StructuredTool]:
    """
    Carga todas las herramientas de todos los wrappers MCP configurados.
    
    Returns:
        Lista consolidada de todas las herramientas LangChain
    """
    logger.info("="*80)
    logger.info("🚀 CARGANDO HERRAMIENTAS MCP DE TODOS LOS WRAPPERS")
    logger.info("="*80)
    
    # Obtener configuración de wrappers
    wrappers_config = settings.get_mcp_wrappers()
    logger.info(f"Wrappers configurados: {list(wrappers_config.keys())}")
    
    all_tools = []
    
    # Cargar herramientas de cada wrapper
    for wrapper_name, lambda_function_name in wrappers_config.items():
        logger.info(f"\n[MCP] Procesando wrapper: {wrapper_name}")
        logger.info(f"[MCP] Lambda: {lambda_function_name}")
        
        try:
            tools = await get_mcp_tools_from_wrapper(wrapper_name, lambda_function_name)
            all_tools.extend(tools)
        except Exception as e:
            logger.error(f"[MCP] ❌ Error cargando {wrapper_name}: {e}")
            # Continuar con los demás wrappers
            continue
    
    logger.info("="*80)
    if all_tools:
        logger.info(f"✅ CARGA COMPLETADA: {len(all_tools)} herramienta(s) total(es)")
        for tool in all_tools:
            wrapper_source = _tool_metadata_map[tool.name].wrapper_source
            logger.info(f"   - {tool.name} (desde {wrapper_source})")
    else:
        logger.error("❌ NO SE CARGARON HERRAMIENTAS")
    logger.info("="*80)
    
    return all_tools


def load_mcp_tools() -> List[StructuredTool]:
    """
    Punto de entrada síncrono para cargar herramientas MCP.
    Se ejecuta en el cold start de Lambda.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tools = loop.run_until_complete(get_all_mcp_tools())
        loop.close()
        return tools
        
    except Exception as e:
        logger.error("="*80)
        logger.error(f"❌ ERROR CRÍTICO cargando herramientas: {e}")
        logger.error("="*80)
        logger.exception(e)
        return []


# 🔥 NUEVO: Mapeo de herramientas a metadata
_tool_metadata_map: Dict[str, MCPToolMetadata] = {}


async def call_mcp_tool(tool_name: str, arguments: Dict) -> str:
    """
    Invoca una herramienta MCP específica en su wrapper correspondiente.

    Args:
        tool_name: Nombre de la herramienta
        arguments: Argumentos para la herramienta

    Returns:
        Resultado de la ejecución
    """
    logger.info("="*80)
    logger.info(f"🔧 INVOCANDO HERRAMIENTA: {tool_name}")
    logger.info("="*80)
    logger.info(f"[TOOL] Type of arguments: {type(arguments)}")
    logger.info(f"[TOOL] Arguments keys: {list(arguments.keys()) if isinstance(arguments, dict) else 'N/A'}")
    logger.info(f"[TOOL] Arguments completo: {json.dumps(arguments, indent=2, default=str)}")

    # 🔥 VALIDACIÓN: Verificar si message_id está presente
    if isinstance(arguments, dict):
        if 'message_id' in arguments and arguments['message_id']:
            logger.info(f"[TOOL] ✅ message_id presente: {arguments['message_id'][:50]}...")
        else:
            logger.error(f"[TOOL] ❌ PROBLEMA: message_id ausente o vacío!")
            logger.error(f"[TOOL] Esto causará error en el wrapper Lambda")

    logger.info("="*80)
    
    # 🔥 Determinar qué Lambda wrapper usar
    if tool_name not in _tool_metadata_map:
        error_msg = f"Herramienta '{tool_name}' no está registrada en ningún wrapper"
        logger.error(f"[TOOL] ❌ {error_msg}")
        logger.error(f"[TOOL] Herramientas disponibles: {list(_tool_metadata_map.keys())}")
        return f"Error: {error_msg}"
    
    metadata = _tool_metadata_map[tool_name]
    lambda_function_name = metadata.wrapper_source
    logger.info(f"[TOOL] Wrapper target: {lambda_function_name}")
    
    try:
        # Invocar herramienta en su wrapper
        response = await invoke_wrapper_lambda(
            lambda_function_name=lambda_function_name,
            method="tools/call",
            params={
                "name": tool_name,
                "arguments": arguments
            }
        )
        
        # Validar error
        if "error" in response:
            error = response["error"]
            error_msg = error.get("message", "Error desconocido")
            error_code = error.get("code", -1)
            
            logger.error("="*80)
            logger.error(f"❌ ERROR EN HERRAMIENTA: {tool_name}")
            logger.error(f"Código: {error_code}")
            logger.error(f"Mensaje: {error_msg}")
            logger.error("="*80)
            
            return f"Error ({error_code}): {error_msg}"
        
        # Extraer resultado
        result = response.get("result", {})
        content = result.get("content", [])
        
        if not content:
            logger.warning(f"[TOOL] Sin contenido en la respuesta")
            return "Sin respuesta del servidor"
        
        result_text = content[0].get("text", "Sin texto")
        
        logger.info("="*80)
        logger.info(f"✅ HERRAMIENTA EJECUTADA: {tool_name}")
        logger.info(f"Resultado ({len(result_text)} caracteres):")
        logger.info("-"*80)
        logger.info(result_text[:500] + ("..." if len(result_text) > 500 else ""))
        logger.info("="*80)
        
        return result_text
        
    except Exception as e:
        logger.error("="*80)
        logger.error(f"❌ EXCEPCIÓN INVOCANDO: {tool_name}")
        logger.error(f"Error: {str(e)}")
        logger.error("="*80)
        logger.exception(e)
        return f"Error: {str(e)}"


# 🔥 Inicializar sistema (ya no necesitamos _build_tool_wrapper_map separado)
def initialize_tool_system():
    """Inicializa el sistema de herramientas MCP"""
    tools = load_mcp_tools()
    # El mapeo ya se construye dentro de get_mcp_tools_from_wrapper
    return tools