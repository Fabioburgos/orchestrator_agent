# core/graph_client.py

import requests
from config.settings import settings
from custom_logging import get_logger
from typing import Optional, Dict, Any

logger = get_logger(__name__)

class GraphClient:
    """
    Cliente para interactuar con Microsoft Graph API.
    Maneja autenticación y peticiones HTTP.
    """

    def __init__(self):
        self.tenant_id = settings.TENANT_ID
        self.client_id = settings.CLIENT_ID
        self.client_secret = settings.CLIENT_SECRET
        self.target_user_email = settings.TARGET_USER_EMAIL
        self.access_token = None
        self.graph_api_endpoint = "https://graph.microsoft.com/v1.0"

    def get_access_token(self) -> Optional[str]:
        """
        Obtiene un token de acceso usando Client Credentials Flow.

        Returns:
            str: Access token si fue exitoso, None en caso de error
        """
        try:
            token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

            token_data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'https://graph.microsoft.com/.default'
            }

            logger.debug("Solicitando token de acceso a Microsoft Graph...")
            response = requests.post(token_url, data = token_data, timeout=10)
            response.raise_for_status()

            token_response = response.json()
            self.access_token = token_response.get('access_token')

            if self.access_token:
                logger.info("Token de acceso obtenido")
                return self.access_token
            else:
                logger.error("No se recibió access_token en la respuesta")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error obteniendo token de acceso: {e}")
            return None

    def make_graph_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Realiza una petición HTTP a Microsoft Graph API.

        Args:
            endpoint: Endpoint relativo (ej: '/users/user@domain.com/messages/messageId')
            method: Método HTTP (GET, POST, PATCH, DELETE)
            data: Datos JSON para el body de la petición (opcional)

        Returns:
            Dict con la respuesta JSON, o None si hay error
        """
        if not self.access_token:
            logger.debug("No hay token disponible, obteniendo uno nuevo...")
            if not self.get_access_token():
                logger.error("No se pudo obtener token de acceso")
                return None

        url = f"{self.graph_api_endpoint}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        try:
            logger.debug(f"{method} {endpoint}")

            if method.upper() == "GET":
                response = requests.get(url, headers = headers, timeout = 30)
            elif method.upper() == "POST":
                response = requests.post(url, headers = headers, json = data, timeout = 30)
            elif method.upper() == "PATCH":
                response = requests.patch(url, headers = headers, json = data, timeout = 30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers = headers, timeout = 30)
            else:
                logger.error(f"Método HTTP no soportado: {method}")
                return None

            response.raise_for_status()

            # Algunos endpoints no devuelven JSON (ej: DELETE)
            if response.status_code == 204:
                return {"success": True}

            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.warning("Token expirado, renovando...")
                self.access_token = None
                return self.make_graph_request(endpoint, method, data)

            logger.error(f"Error HTTP en petición a Graph API: {e}")
            logger.error(f"Response: {e.response.text if e.response else 'No response'}")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición a Graph API: {e}")
            return None