# handler.py

import os # <-- Añadir esta línea
from dotenv import load_dotenv

# --- PRUEBA DE FUEGO ---
# Cargamos el fichero .env
print("Paso 1: Intentando cargar el fichero .env...")
load_dotenv()
print("Paso 2: Fichero .env procesado.")

# Ahora, verificamos inmediatamente si las variables existen
api_key = os.getenv("AZURE_OPENAI_API_KEY")
mcp_config = os.getenv("MCP_SERVERS_CONFIG")

print(f"Paso 3: Verificando variables...")
print(f"   -> ¿Se encontró AZURE_OPENAI_API_KEY? {'Sí' if api_key else 'NO'}")
print(f"   -> ¿Se encontró MCP_SERVERS_CONFIG? {'Sí' if mcp_config else 'NO'}")

# Si la clave de API no se encuentra, detenemos todo aquí con un error claro.
if not api_key:
    raise ValueError("ERROR CRÍTICO: No se pudo cargar AZURE_OPENAI_API_KEY desde el fichero .env. Por favor, verifica que el fichero .env está en la carpeta raíz del proyecto y que la variable está escrita correctamente.")

print("Paso 4: Las variables de entorno parecen estar cargadas. Procediendo a importar el resto de módulos...")
# -------------------------

# Ahora, el resto de los imports
import json
import re
from src.graph import build_graph
from src.state import AgentState
from langchain_core.messages import HumanMessage

app = build_graph()
print("Grafo de LangGraph compilado. Lambda lista para invocaciones.")

async def lambda_handler(event, context):
    # ... (el resto de la función es correcta)
    # ...
    # (No es necesario pegar el resto del código, no cambia)
    print(f"Evento recibido: {json.dumps(event)}")

    try:
        body = json.loads(event.get("body", "{}"))
        notification = body.get("value", [{}])[0]
        resource_path = notification.get("resource", "")
        
        match = re.search(r"messages\('([^']+)'\)", resource_path, re.IGNORECASE)
        if not match:
            raise ValueError(f"No se pudo extraer el message_id de: {resource_path}")
        
        message_id = match.group(1)
        print(f"Message ID extraído: {message_id}")

    except Exception as e:
        error_message = f"Error al procesar la notificación de Graph API: {e}"
        print(error_message)
        return {"statusCode": 400, "body": json.dumps({"error": error_message})}

    initial_prompt = (
        f"Ha llegado una notificación de un nuevo email con ID '{message_id}'. "
        "Decide qué herramienta es la adecuada para procesar este mensaje e invócala pasándole el message_id."
    )
    
    initial_state: AgentState = {
        "messages": [HumanMessage(content=initial_prompt)],
        "message_id": message_id,
        "original_notification": notification
    }
    
    print("Invocando el grafo de LangGraph...")
    final_state = await app.ainvoke(initial_state)
    print("Ejecución del grafo completada.")

    final_response_content = str(final_state["messages"][-1].content)
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Proceso de orquestación completado para message_id: {message_id}",
            "final_state_summary": final_response_content
        })
    }