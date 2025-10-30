# src/tool_loader.py

import os
import json
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

async def _load_tools_async():
    """
    Función asíncrona interna para cargar las herramientas.
    """
    config_str = os.getenv("MCP_SERVERS_CONFIG")
    if not config_str:
        print("ADVERTENCIA: La variable de entorno MCP_SERVERS_CONFIG no está definida.")
        return []

    try:
        servers_config = json.loads(config_str) # Parsear la configuración JSON desde la variable de entorno
    except json.JSONDecodeError:
        print("ERROR: Fallo al parsear MCP_SERVERS_CONFIG. Asegúrate de que es un JSON válido.")
        return []

    print("Configuración de servidores MCP cargada. Inicializando cliente...")

    client = MultiServerMCPClient(servers_config) # Crear el cliente con la configuración

    tools = await client.get_tools() # El cliente se conecta a todas las URLs/procesos y obtiene las herramientas
    
    print(f"Descubrimiento completado. Se cargaron {len(tools)} herramienta(s).")
    for tool in tools:
        print(f"-> Herramienta disponible: '{tool.name}'")
        
    return tools

def load_mcp_tools():
    """
    Punto de entrada síncrono para ser llamado durante la inicialización de la Lambda.
    Ejecuta la lógica asíncrona de carga de herramientas.
    """
    return asyncio.run(_load_tools_async())