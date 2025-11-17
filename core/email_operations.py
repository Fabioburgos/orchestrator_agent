# core/email_operations.py

from custom_logging import get_logger
from typing import Optional, Dict, Any
from core.graph_client import GraphClient

logger = get_logger(__name__)

class EmailOperations:
    """
    Operaciones relacionadas con emails usando Microsoft Graph API.
    """

    def __init__(self, graph_client: Optional[GraphClient] = None):
        """
        Args:
            graph_client: Instancia de GraphClient. Si no se proporciona, se crea una nueva.
        """
        self.graph_client = graph_client or GraphClient()

    def get_full_email(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene todos los datos del email incluyendo attachments.

        Args:
            message_id: ID del mensaje en Microsoft Graph

        Returns:
            Dict con 'message' y 'attachments', o None si hay error
        """
        try:
            logger.info(f"Obteniendo email completo: {message_id[:20]}...")

            # Intentar obtener el mensaje con attachments expandidos
            message_data = self.graph_client.make_graph_request(
                f'/users/{self.graph_client.target_user_email}/messages/{message_id}?$expand=attachments'
            )

            if not message_data:
                logger.error(f"No se pudo obtener el email {message_id}")
                return None

            # Obtener attachments por separado si no vinieron en el expand
            attachments_data = []
            if 'attachments' not in message_data or not message_data['attachments']:
                logger.debug("Obteniendo attachments por separado...")
                attachments_response = self.graph_client.make_graph_request(
                    f'/users/{self.graph_client.target_user_email}/messages/{message_id}/attachments'
                )

                if attachments_response and 'value' in attachments_response:
                    attachments_data = attachments_response['value']
            else:
                attachments_data = message_data.get('attachments', [])

            logger.info(f"Email obtenido: {len(attachments_data)} adjuntos")

            return {
                'message': message_data,
                'attachments': attachments_data
            }

        except Exception as e:
            logger.exception(f"Error obteniendo email completo: {e}")
            return None

    def extract_email_fields(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrae los campos importantes de un mensaje de Graph API.

        Args:
            message_data: Datos crudos del mensaje desde Graph API

        Returns:
            Dict con subject, body, sender, etc.
        """
        subject = message_data.get('subject', 'Sin asunto')

        # Extraer body
        body_data = message_data.get('body', {})
        body_content = body_data.get('content', '')
        body_type = body_data.get('contentType', 'text')

        # Extraer remitente
        sender = 'Desconocido'
        from_field = message_data.get('from')
        if from_field and from_field.get('emailAddress'):
            sender = from_field['emailAddress'].get('address', 'Desconocido')

        # Extraer otros campos útiles
        received_datetime = message_data.get('receivedDateTime', '')
        has_attachments = message_data.get('hasAttachments', False)

        return {
            'subject': subject,
            'body_content': body_content,
            'body_type': body_type,
            'sender': sender,
            'received_datetime': received_datetime,
            'has_attachments': has_attachments
        }