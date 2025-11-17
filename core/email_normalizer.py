# utils/email_normalizer.py

import re
import unicodedata
import pandas as pd
from typing import List, Dict
from collections import Counter
from custom_logging import get_logger

logger = get_logger(__name__)

class EmailBodyNormalizer:
    """
    Normalizador de cuerpos de correo para estandarizar el texto y mejorar la clasificación automática.
    """
    def __init__(self):
        # ===== PATRONES PARA ELIMINAR FIRMAS Y DISCLAIMERS =====
        self.signature_patterns = [
            # Disclaimers legales comunes (CRÍTICO - AGREGAR PRIMERO)
            r'DISCLAIMER\s*/\s*AVISO\s+LEGAL:.*',
            r'DISCLAIMER:.*',
            r'AVISO\s+LEGAL:.*',
            r'CONFIDENCIALIDAD:.*',
            r'(?:Este mensaje|Esta comunicación|This message|This email).*?(?:confidencial|privilegiada|privada).*',
            
            # Avisos de confidencialidad largos (GBM, SIMAN, etc)
            r'La información contenida en este mensaje.*',
            r'Si usted no es el destinatario.*',
            r'Si responde a este mensaje.*',
            
            # Patrones generales de confidencialidad
            r'(?:Este correo|Este email|This email).*?(?:confidencial|privilegiada|confidentiality).*',
            r'^(?:Muchas gracias|Gracias|Saludos|Atentamente|Cordialmente|Regards|Best regards)[\.,]?.*',
            
            # Nombre + Cargo + Empresa (formato típico de firma)
            r'(?:^|\n)[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+\s*\n\s*(?:Director|Directora|Gerente|Coordinador|Coordinadora|Jefe|Jefa|Analista|Ingeniero|Ingeniera|Licenciado|Licenciada).*',
            
            # Información de contacto con emojis
            r'[📧📱🏢🌐💼]\s*[\w\s\:\@\.\-\+\(\)\/]+',
            
            # Información de contacto estructurada
            r'T\.\s*[\d\-\+\(\)]+',
            r'Tel[:\.]?\s*[\d\-\+\(\)]+',
            r'Cel[:\.]?\s*[\d\-\+\(\)]+',
            r'(?:Email|E-mail|Correo)[:\s]+[\w\.\-]+@[\w\.\-]+',
            r'(?:Teléfono|Telefono|Phone)[:\s]*[\d\-\+\(\)]+',
            r'(?:Teléfono|Telefono|Phone)[:\s]*[\d\-\+\(\)]+',
            r'(?:Móvil|Movil|Mobile|Cel)[:\s]*[\d\-\+\(\)]+',
            
            # Separadores visuales (más agresivo)
            r'[─━═_\-]{3,}',
            
            # Patrón 21: Emojis de redes sociales y slogans
            r'^[🤝💚📱🌐💼🚀🌱].*',
            
            # Avisos de "no imprimir" / ecológicos
            r'(?:Antes de imprimir|Before printing).*',
            r'(?:Piense|Think).*?(?:medio ambiente|environment|planeta|planet).*',
            
            # Firmas con redes sociales
            r'(?:Síguenos|Siguenos|Follow us|Encuéntranos).*',
            r'(?:Facebook|Twitter|LinkedIn|Instagram).*',
            
            # URLs de sitios web
            r'(?:www\.|https?://)\S+',
            
            # Firmas con nombres de empresas comunes
            r'(?:GBM|Siman|Almacenes Siman).*?(?:todos los derechos|all rights|reserved).*',
            
            # Avisos de virus/seguridad
            r'(?:Este mensaje ha sido|This message has been).*?(?:escaneado|scanned).*?(?:virus|malware).*',
            
            # Política de privacidad
            r'(?:Política de privacidad|Privacy policy).*',
            
            # "Enviado desde" (móvil)
            r'Enviado\s+desde\s+(?:mi|my).*?(?:iPhone|iPad|Android|BlackBerry|Samsung).*',
            r'Sent\s+from\s+(?:my|my).*?(?:iPhone|iPad|Android|BlackBerry|Samsung).*',
        ]
        
        # Patrones de ruido común en emails
        self.noise_patterns = [
            r'Se comparte cuerpo del correo del usuario:.*?Nota:',
            r'Nota: se adjunta correo donde se brinde más información.*',
            r'Se adjunta correo con más detalle',
            r'Se adjunta cuerpo de correo:',
            r'INFORMACIÓN DEL USUARIO\..*?PASS: \*+',
            r'Nombre completo.*?País.*?Usuarios VPN.*?(\w+\s+\w+.*?\w+\.\w+.*?)*',
            r'Saludos,?\s*Gracias\.?',
            r'Quedamos atentos.*?Saludos cordiales\.',
            r'En espera de sus comentarios\.\s*Gracias',
            r'Quedo a la orden\s*Saludos',
            r'Contact Center - Almacenes Siman',
            r'T\. \d{4}-\d{4}',
            r'Sinceramente,',
            r'Buenos días,?|Buenas tardes,?|Buen día,?',
            r'Estimados:?',
            r'@\w+\s+\w+\s+\w+',
            r'Adjunto.*?formulario',
            r'Se adjunt[ao].*?formulario',
        ]
        
        # Patrones para extraer información estructurada
        self.structured_patterns = {
            'usuario': r'[Uu]suario:?\s*(\w+)',
            'nombre': r'[Nn]ombre:?\s*([A-Za-z\s]+)',
            'dui': r'DUI:?\s*(\d{8}-\d)',
            'telefono': r'[Tt]eléfono:?\s*(\d+)',
            'correo': r'[Cc]orreo:?\s*(\w+@\w+\.\w+)',
            'sistema': r'sistema|aplicación|app',
            'desbloqueo': r'desbloque[ao]',
            'renovacion': r'renovación|renovar',
            'creacion': r'creación|crear|nuevo',
            'baja': r'baja|dar de baja|desactivar',
            'cambio': r'cambio|modificar|actualizar',
            'acceso': r'acceso|acceder|autorización',
            'vpn': r'VPN',
            'licencia': r'licencia',
            'contraseña': r'contraseña|password|clave',
            'tarjeta': r'tarjeta',
        }
        
        # Stopwords específicas del dominio
        self.domain_stopwords = {
            'siman', 'almacenes', 'costa', 'rica', 'salvador', 'guatemala',
            'estimados', 'saludos', 'gracias', 'favor', 'apoyo', 'ayuda',
            'correo', 'formulario', 'adjunto', 'comparto', 'solicito',
            'buen', 'dia', 'buenas', 'tardes', 'buenos', 'dias',
            'nota', 'informacion', 'detalle', 'orden', 'atentos'
        }
        
        # Patrones de ruido común en emails
        self.noise_patterns = [
            r'Se comparte cuerpo del correo del usuario:.*?Nota:',
            r'Nota: se adjunta correo donde se brinde más información.*',
            r'Se adjunta correo con más detalle',
            r'Se adjunta cuerpo de correo:',
            r'INFORMACIÓN DEL USUARIO\..*?PASS: \*+',
            r'Nombre completo.*?País.*?Usuarios VPN.*?(\w+\s+\w+.*?\w+\.\w+.*?)*',
            r'Saludos,?\s*Gracias\.?',
            r'Quedamos atentos.*?Saludos cordiales\.',
            r'En espera de sus comentarios\.\s*Gracias',
            r'Quedo a la orden\s*Saludos',
            r'Contact Center - Almacenes Siman',
            r'T\. \d{4}-\d{4}',
            r'Sinceramente,',
            r'Buenos días,?|Buenas tardes,?|Buen día,?',
            r'Estimados:?',
            r'@\w+\s+\w+\s+\w+',
            r'Adjunto.*?formulario',
            r'Se adjunt[ao].*?formulario',
        ]
        
        # Patrones para extraer información estructurada
        self.structured_patterns = {
            'usuario': r'[Uu]suario:?\s*(\w+)',
            'nombre': r'[Nn]ombre:?\s*([A-Za-z\s]+)',
            'dui': r'DUI:?\s*(\d{8}-\d)',
            'telefono': r'[Tt]eléfono:?\s*(\d+)',
            'correo': r'[Cc]orreo:?\s*(\w+@\w+\.\w+)',
            'sistema': r'sistema|aplicación|app',
            'desbloqueo': r'desbloque[ao]',
            'renovacion': r'renovación|renovar',
            'creacion': r'creación|crear|nuevo',
            'baja': r'baja|dar de baja|desactivar',
            'cambio': r'cambio|modificar|actualizar',
            'acceso': r'acceso|acceder|autorización',
            'vpn': r'VPN',
            'licencia': r'licencia',
            'contraseña': r'contraseña|password|clave',
            'tarjeta': r'tarjeta',
        }
        
        # Stopwords específicas del dominio
        self.domain_stopwords = {
            'siman', 'almacenes', 'costa', 'rica', 'salvador', 'guatemala',
            'estimados', 'saludos', 'gracias', 'favor', 'apoyo', 'ayuda',
            'correo', 'formulario', 'adjunto', 'comparto', 'solicito',
            'buen', 'dia', 'buenas', 'tardes', 'buenos', 'dias',
            'nota', 'informacion', 'detalle', 'orden', 'atentos'
        }

    def remove_signatures_and_disclaimers(self, text: str) -> str:
        """
        Elimina firmas empresariales y disclaimers del texto.
        """
        cleaned_text = text

        logger.debug("=== LIMPIEZA DE FIRMAS Y DISCLAIMERS ===")
        logger.debug(f"Texto original length: {len(text)}")

        # 1. Detectar punto de corte de despedida
        despedida_patterns = [
            r'Muchas gracias por su apoyo',
            r'Gracias por su ayuda',
            r'Saludos cordiales',
            r'Atentamente',
            r'Cordialmente',
            r'Quedo atento',
            r'Quedamos atentos',
        ]

        earliest_cutoff = len(cleaned_text)
        for pattern in despedida_patterns:
            match = re.search(pattern, cleaned_text, re.IGNORECASE)
            if match and match.start() < earliest_cutoff:
                earliest_cutoff = match.start()
                logger.debug(f"Punto de corte encontrado en: {pattern} (posición {match.start()})")

        # Si encontramos despedida, cortar desde ahí
        if earliest_cutoff < len(cleaned_text):
            cleaned_text = cleaned_text[:earliest_cutoff].strip()
            logger.debug(f"Texto cortado desde despedida: {len(cleaned_text)} caracteres")

        # 2. Aplicar patrones de firma uno por uno
        for i, pattern in enumerate(self.signature_patterns):
            try:
                before_length = len(cleaned_text)
                matches = list(re.finditer(pattern, cleaned_text, flags=re.IGNORECASE | re.DOTALL | re.MULTILINE))

                if matches:
                    for match in matches:
                        removed_text = match.group(0)
                        if len(removed_text) > 20:  # Solo loggear si es significativo
                            preview = removed_text[:80].replace('\n', ' ')
                            logger.debug(f"Patrón {i+1} eliminó: '{preview}...'")

                cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE | re.DOTALL | re.MULTILINE)

                after_length = len(cleaned_text)
                if before_length != after_length:
                    logger.debug(f"  Reducción: {before_length} -> {after_length} caracteres")

            except Exception as e:
                logger.error(f"Error en patrón {i+1}: {e}")
                continue

        # 3. Limpiar espacios múltiples resultantes
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        cleaned_text = cleaned_text.strip()

        logger.debug(f"Texto después de limpiar firmas length: {len(cleaned_text)}")

        return cleaned_text

    def remove_noise(self, text: str) -> str:
        """Elimina patrones de ruido comunes en los emails."""
        cleaned_text = text
        
        for pattern in self.noise_patterns:
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE | re.DOTALL)
        
        return cleaned_text.strip()

    def normalize_unicode(self, text: str) -> str:
        """Normaliza caracteres Unicode y acentos."""
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))
        return text

    def standardize_whitespace(self, text: str) -> str:
        """Estandariza espacios en blanco y saltos de línea."""
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    def extract_key_actions(self, text: str) -> List[str]:
        """Extrae las acciones clave del texto."""
        actions = []
        text_lower = text.lower()
        
        action_keywords = {
            'crear': ['crear', 'creacion', 'nuevo', 'nueva', 'alta'],
            'modificar': ['modificar', 'cambiar', 'cambio', 'actualizar'],
            'desbloquear': ['desbloquear', 'desbloqueo', 'restablecer'],
            'renovar': ['renovar', 'renovacion'],
            'eliminar': ['eliminar', 'baja', 'dar de baja', 'desactivar'],
            'acceder': ['acceso', 'acceder', 'autorizacion', 'habilitar'],
            'solicitar': ['solicitar', 'solicitud', 'requiere', 'necesita']
        }
        
        for action, keywords in action_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                actions.append(action)
        
        return actions

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extrae entidades estructuradas del texto."""
        entities = {}
        
        for entity_type, pattern in self.structured_patterns.items():
            if entity_type in ['sistema', 'desbloqueo', 'renovacion', 'creacion', 'baja', 'cambio', 'acceso', 'vpn', 'licencia', 'contraseña', 'tarjeta']:
                # Para conceptos, solo verificar presencia
                if re.search(pattern, text, re.IGNORECASE):
                    entities[entity_type] = ['presente']
            else:
                # Para datos específicos, extraer valores
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    entities[entity_type] = matches
        
        return entities

    def create_normalized_features(self, text: str) -> Dict[str, any]:
        """Crea características normalizadas del texto."""
        entities = self.extract_entities(text)
        actions = self.extract_key_actions(text)
        
        features = {
            'tiene_usuario': 'usuario' in entities,
            'tiene_nombre': 'nombre' in entities,
            'tiene_dui': 'dui' in entities,
            'tiene_sistema': 'sistema' in entities,
            'accion_crear': 'crear' in actions,
            'accion_modificar': 'modificar' in actions,
            'accion_desbloquear': 'desbloquear' in actions,
            'accion_renovar': 'renovar' in actions,
            'accion_eliminar': 'eliminar' in actions,
            'accion_acceder': 'acceder' in actions,
            'accion_solicitar': 'solicitar' in actions,
            'involucra_vpn': 'vpn' in entities,
            'involucra_licencia': 'licencia' in entities,
            'involucra_contraseña': 'contraseña' in entities,
            'involucra_tarjeta': 'tarjeta' in entities,
            'num_acciones': len(actions),
            'num_entidades': len(entities)
        }
        
        return features

    def normalize_email_body(self, text: str) -> Dict[str, any]:
        """
        Normaliza completamente el cuerpo del correo.
        """
        logger.info("="*80)
        logger.info("INICIANDO NORMALIZACIÓN COMPLETA")
        logger.info("="*80)

        # 1. Eliminar firmas y disclaimers (NUEVO - PRIMERO)
        logger.info(">>> PASO 1: Eliminando firmas y disclaimers...")
        text_sin_firmas = self.remove_signatures_and_disclaimers(text)
        logger.info(f"Resultado: {len(text)} -> {len(text_sin_firmas)} caracteres")

        # 2. Limpieza básica de ruido
        logger.info(">>> PASO 2: Limpiando ruido...")
        normalized_text = self.remove_noise(text_sin_firmas)

        # 3. Normalizar unicode
        logger.info(">>> PASO 3: Normalizando unicode...")
        normalized_text = self.normalize_unicode(normalized_text)

        # 4. Estandarizar espacios
        logger.info(">>> PASO 4: Estandarizando espacios...")
        normalized_text = self.standardize_whitespace(normalized_text)

        # 5. Extracción de características (del texto original)
        logger.info(">>> PASO 5: Extrayendo características...")
        features = self.create_normalized_features(text)

        # 6. Crear resumen estructurado
        entities = self.extract_entities(text)
        actions = self.extract_key_actions(text)

        # 7. Generar texto normalizado final (contenido esencial)
        logger.info(">>> PASO 7: Extrayendo contenido esencial...")
        essential_text = self.extract_essential_content(normalized_text)

        logger.info("="*80)
        logger.info("NORMALIZACIÓN COMPLETADA")
        logger.info("="*80)
        logger.info(f"Texto original: {len(text)} caracteres")
        logger.info(f"Texto sin firmas: {len(text_sin_firmas)} caracteres")
        logger.info(f"Texto final: {len(essential_text)} caracteres")
        reduction_pct = ((len(text) - len(essential_text)) / len(text) * 100) if len(text) > 0 else 0
        logger.info(f"Reducción total: {len(text) - len(essential_text)} caracteres ({reduction_pct:.1f}%)")
        logger.debug(f"\nTexto final limpio:\n{essential_text}\n")

        return {
            'texto_normalizado': essential_text,
            'texto_limpio': normalized_text,
            'texto_sin_firmas': text_sin_firmas,
            'acciones': actions,
            'entidades': entities,
            'caracteristicas': features,
            'texto_original': text,
            'estadisticas': {
                'longitud_original': len(text),
                'longitud_sin_firmas': len(text_sin_firmas),
                'longitud_final': len(essential_text),
                'reduccion_porcentaje': reduction_pct
            }
        }

    def extract_essential_content(self, text: str) -> str:
        """Extrae solo el contenido esencial del correo."""
        # Remover frases de cortesía comunes
        courtesy_patterns = [
            r'buen día|buenos días|buenas tardes',
            r'estimados?:?',
            r'saludos,?\s*gracias',
            r'quedo a la orden',
            r'quedamos atentos',
            r'en espera de sus comentarios',
            r'un placer saludarle',
            r'agradeceré su ayuda',
            r'de su valiosa ayuda'
        ]
        
        essential_text = text
        for pattern in courtesy_patterns:
            essential_text = re.sub(pattern, '', essential_text, flags=re.IGNORECASE)
        
        # Limpiar espacios resultantes
        essential_text = self.standardize_whitespace(essential_text)
        
        return essential_text

    def batch_normalize(self, df: pd.DataFrame, text_column: str = 'descripcion') -> pd.DataFrame:
        """Normaliza un DataFrame completo de correos."""
        results = []
        
        for idx, row in df.iterrows():
            text = row[text_column]
            normalized = self.normalize_email_body(text)
            
            # Crear fila con datos normalizados
            new_row = row.copy()
            new_row['texto_normalizado'] = normalized['texto_normalizado']
            new_row['texto_limpio'] = normalized['texto_limpio']
            new_row['acciones_detectadas'] = '|'.join(normalized['acciones'])
            new_row['entidades_detectadas'] = '|'.join(normalized['entidades'].keys())
            
            # Agregar características como columnas
            for feature, value in normalized['caracteristicas'].items():
                new_row[f'feature_{feature}'] = value
                
            results.append(new_row)
        
        return pd.DataFrame(results)

# Función para análisis de normalización
def analyze_normalization_impact(original_df: pd.DataFrame, normalized_df: pd.DataFrame):
    """Analiza el impacto de la normalización en los datos."""
    logger.info("=== ANÁLISIS DE NORMALIZACIÓN ===\n")

    # Estadísticas básicas
    logger.info("1. ESTADÍSTICAS BÁSICAS:")
    logger.info(f"Emails procesados: {len(original_df)}")

    # Longitud promedio antes y después
    orig_lengths = original_df['descripcion'].str.len()
    norm_lengths = normalized_df['texto_normalizado'].str.len()

    logger.info(f"Longitud promedio original: {orig_lengths.mean():.1f} caracteres")
    logger.info(f"Longitud promedio normalizada: {norm_lengths.mean():.1f} caracteres")
    reduction_avg = ((orig_lengths.mean() - norm_lengths.mean()) / orig_lengths.mean() * 100)
    logger.info(f"Reducción promedio: {reduction_avg:.1f}%")

    # Análisis de acciones detectadas
    logger.info("\n2. ACCIONES MÁS COMUNES:")
    all_actions = []
    for actions_str in normalized_df['acciones_detectadas']:
        if pd.notna(actions_str) and actions_str:
            all_actions.extend(actions_str.split('|'))

    action_counts = Counter(all_actions)
    for action, count in action_counts.most_common(10):
        logger.info(f"   {action}: {count} veces")

    # Análisis de entidades
    logger.info("\n3. ENTIDADES MÁS COMUNES:")
    all_entities = []
    for entities_str in normalized_df['entidades_detectadas']:
        if pd.notna(entities_str) and entities_str:
            all_entities.extend(entities_str.split('|'))

    entity_counts = Counter(all_entities)
    for entity, count in entity_counts.most_common(10):
        logger.info(f"   {entity}: {count} veces")