# config/settings.py

import json
from pydantic import Field, field_validator
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Dict

load_dotenv()

class Settings(BaseSettings):
    # Azure OpenAI
    AZURE_OPENAI_DEPLOYMENT_NAME: str
    AZURE_OPENAI_API_VERSION: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_KEY: str = Field(..., repr=False)

    # Microsoft Graph API
    MICROSOFT_GRAPH_TENANT_ID: str
    MICROSOFT_GRAPH_CLIENT_ID: str
    MICROSOFT_GRAPH_CLIENT_SECRET: str = Field(..., repr=False)

    # Dominio Autorizado
    DOMINIO_AUTORIZADO: str
    TARGET_USER_EMAIL: str
    
    # 🔥 NUEVO: Configuración de MCP Wrappers
    # Formato JSON: {"nombre": "lambda-function-name", ...}
    MCP_WRAPPERS: str = Field(
        default='{"email-classifier": "dev-mcp-wrapper-email-classifier-2"}',
        description="JSON con mapeo de wrappers MCP a nombres de Lambda"
    )
    
    # Región de AWS para Lambda
    AWS_REGION: str = Field(default="us-east-2")

    @property
    def TENANT_ID(self) -> str:
        return self.MICROSOFT_GRAPH_TENANT_ID

    @property
    def CLIENT_ID(self) -> str:
        return self.MICROSOFT_GRAPH_CLIENT_ID

    @property
    def CLIENT_SECRET(self) -> str:
        return self.MICROSOFT_GRAPH_CLIENT_SECRET
    
    @field_validator('MCP_WRAPPERS')
    @classmethod
    def validate_mcp_wrappers(cls, v: str) -> str:
        """Valida que MCP_WRAPPERS sea JSON válido"""
        try:
            parsed = json.loads(v)
            if not isinstance(parsed, dict):
                raise ValueError("MCP_WRAPPERS debe ser un objeto JSON")
            return v
        except json.JSONDecodeError as e:
            raise ValueError(f"MCP_WRAPPERS no es JSON válido: {e}")
    
    def get_mcp_wrappers(self) -> Dict[str, str]:
        """
        Retorna el diccionario de wrappers MCP parseado.
        
        Returns:
            Dict con formato: {"nombre-wrapper": "lambda-function-name"}
        """
        return json.loads(self.MCP_WRAPPERS)
    
    def get_wrapper_lambda_name(self, wrapper_name: str) -> str:
        """
        Obtiene el nombre de la función Lambda para un wrapper específico.
        
        Args:
            wrapper_name: Nombre del wrapper (ej: "email-classifier")
        
        Returns:
            Nombre de la función Lambda
        
        Raises:
            KeyError: Si el wrapper no está configurado
        """
        wrappers = self.get_mcp_wrappers()
        if wrapper_name not in wrappers:
            raise KeyError(f"Wrapper '{wrapper_name}' no está configurado en MCP_WRAPPERS")
        return wrappers[wrapper_name]
    
settings = Settings()