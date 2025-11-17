# handler.py

import re
import json
import asyncio
from src.state import AgentState
from src.graph import build_graph
from custom_logging import get_logger
from core.llm_client import load_prompt_template
from core.email_operations import EmailOperations
from core.email_processing import EmailProcessing

logger = get_logger(__name__)

app = build_graph()
logger.info("Lambda lista")

# Inicializar servicios de email una sola vez durante el inicio en frío
email_ops = EmailOperations()
email_processor = EmailProcessing()

# Cargamos la plantilla una sola vez durante el inicio en frío
ROUTING_PROMPT_TEMPLATE = load_prompt_template("routing_prompt.txt")

async def async_handler(event, context):
    """
    Punto de entrada de la Lambda para orquestar el procesamiento de notificaciones de Graph API.
    """
    logger.debug(f"Evento recibido: {json.dumps(event)}")

    # Manejar validación de suscripción de Microsoft Graph
    query_params = event.get("queryStringParameters", {}) or {}
    validation_token = query_params.get("validationToken")

    if validation_token:
        logger.info("Solicitud de validación de suscripción recibida")
        # Microsoft Graph requiere que devolvamos el validationToken en texto plano
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/plain"},
            "body": validation_token
        }

    try:
        body = json.loads(event.get("body", "{}"))
        notification = body.get("value", [{}])[0]
        resource_path = notification.get("resource", "")

        # Intentar extraer el message_id de diferentes formatos:
        # Formato 1: messages('ID') o Messages('ID')
        # Formato 2: Users/GUID/Messages/ID
        match = re.search(r"messages\('([^']+)'\)", resource_path, re.IGNORECASE)
        if not match:
            # Intentar formato alternativo: Users/.../Messages/ID
            match = re.search(r"/Messages/([^/]+)$", resource_path, re.IGNORECASE)

        if not match:
            raise ValueError(f"No se pudo extraer el message_id de: {resource_path}")

        message_id = match.group(1)
        logger.info(f"Message ID extraído: {message_id}")

    except Exception as e:
        error_message = f"Error al procesar la notificación de Graph API: {e}"
        logger.exception(error_message)
        return {"statusCode": 400, "body": json.dumps({"error": error_message})}

    # Obtener el email completo desde Microsoft Graph
    logger.info(f"Obteniendo email desde Graph API...")
    email_data = email_ops.get_full_email(message_id)

    if not email_data:
        error_message = f"No se pudo obtener el email {message_id} desde Graph API"
        logger.error(error_message)
        return {"statusCode": 500, "body": json.dumps({"error": error_message})}

    # Extraer campos del mensaje
    message_fields = email_ops.extract_email_fields(email_data['message'])
    subject = message_fields['subject']
    sender = message_fields['sender']

    # Procesar el body del email (convertir HTML a texto, limpiar firmas)
    email_body = email_processor.process_email_body(
        message_fields['body_content'],
        message_fields['body_type']
    )

    logger.info(f"Email de {sender}: '{subject}' ({len(email_body)} chars)")

    initial_messages = ROUTING_PROMPT_TEMPLATE.format_messages(
        subject = subject,
        message_id = message_id,
        email_body = email_body,
        sender = sender
    )

    # 🔥 Log de validación
    logger.info(f"Message ID que se pasará al LLM: {message_id}")
    logger.debug(f"Prompt formateado correctamente con message_id: {message_id[:50]}...")

    initial_state: AgentState = {
        "messages": initial_messages,
        "message_id": message_id,
        "original_notification": notification
    }

    final_state = await app.ainvoke(initial_state)

    final_response_content = str(final_state["messages"][-1].content)
    logger.info(f"Procesamiento completado: {final_response_content}")
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Proceso de orquestación completado para message_id: {message_id}",
            "final_state_summary": final_response_content
        })
    }

def lambda_handler(event, context):
    """
    Wrapper sincrónico para el handler asíncrono.
    AWS Lambda ejecuta esta función y nosotros manejamos el async internamente.
    """
    return asyncio.run(async_handler(event, context))