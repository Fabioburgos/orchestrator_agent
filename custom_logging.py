import sys
import logging
from typing import Optional

def setup_logger(name: str, level: int = logging.INFO, log_format: Optional[str] = None, log_file: Optional[str] = None) -> logging.Logger:
    """
    Configura y prepara un logger.

    Args:
        name: Nombre del logger
        level: Nivel de logging (por defecto: INFO)
        log_format: Cadena de formato de log personalizada (opcional)
        log_file: Ruta al archivo de log (opcional, escribe en consola si no se proporciona)

    Returns:
        Instancia de logger configurada
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Evitar agregar manejadores varias veces
    if logger.handlers:
        return logger

    # Formato por defecto
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(log_format)

    # Manejador de consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Manejador de archivo (opcional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Obtener una instancia de logger configurada.

    Args:
        name: Nombre del logger
        level: Nivel de logging (por defecto: INFO)

    Returns:
        Instancia de logger configurada
    """
    return setup_logger(name, level=level)


# Logger por defecto del módulo
logger = setup_logger(__name__)