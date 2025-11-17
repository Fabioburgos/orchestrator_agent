# core/email_processing.py

import re
from custom_logging import get_logger
from .email_normalizer import EmailBodyNormalizer

logger = get_logger(__name__)

class EmailProcessing:
    """
    Procesamiento y limpieza de contenido de emails.
    """
    def __init__(self):
        self.normalizer = EmailBodyNormalizer()

    def extract_plain_text_from_html(self, html_content: str) -> str:
        """
        Extrae texto plano de contenido HTML.

        Args:
            html_content: Contenido HTML del email

        Returns:
            Texto plano sin tags HTML
        """
        try:
            if not html_content:
                return ''

            # Remover tags HTML
            text = re.sub(r'<[^>]+>', '', html_content)

            # Decodificar entidades HTML comunes
            html_entities = {
                '&nbsp;': ' ',
                '&amp;': '&',
                '&lt;': '<',
                '&gt;': '>',
                '&quot;': '"',
                '&#39;': "'",
                '&apos;': "'",
            }

            for entity, char in html_entities.items():
                text = text.replace(entity, char)

            # Limpiar espacios múltiples y saltos de línea excesivos
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()

            return text

        except Exception as e:
            logger.error(f"Error extrayendo texto plano: {str(e)}")
            return html_content

    def clean_email_body(self, body_text: str) -> str:
        """
        Limpia el cuerpo del email eliminando firmas empresariales, disclaimers y ruido.

        Args:
            body_text: Texto del cuerpo del email

        Returns:
            Texto limpio sin firmas ni disclaimers
        """
        try:
            if not body_text:
                return ''
            
            logger.info("LIMPIANDO CUERPO DE EMAIL")
            logger.info(f"Longitud original: {len(body_text)} caracteres")
            
            # Usar el normalizador para limpiar el texto
            normalized_data = self.normalizer.normalize_email_body(body_text)

            # Obtener el texto normalizado (sin firmas, sin acentos, sin ruido)
            cleaned_text = normalized_data['texto_normalizado']

            logger.info(f"Longitud limpia: {len(cleaned_text)} caracteres")
            logger.info(f"Reducción: {normalized_data['estadisticas']['reduccion_porcentaje']:.1f}%")
            logger.info(f"\nTexto limpio: {cleaned_text[:200]}...")

            return cleaned_text
        
        except Exception as e:
            logger.error(f"Error limpiando cuerpo de email: {str(e)}")
            return body_text

    def process_email_body(self, body_content: str, body_type: str = 'html') -> str:
        """
        Procesa el cuerpo del email: convierte HTML a texto y limpia.

        Args:
            body_content: Contenido crudo del body
            body_type: Tipo de contenido ('html' o 'text')

        Returns:
            Texto limpio y procesado
        """
        # Si es HTML, convertir a texto plano primero
        if body_type.lower() == 'html':
            logger.debug("Convirtiendo HTML a texto plano...")
            plain_text = self.extract_plain_text_from_html(body_content)
        else:
            plain_text = body_content

        # Limpiar el texto (eliminar firmas, etc.)
        cleaned_text = self.clean_email_body(plain_text)

        return cleaned_text