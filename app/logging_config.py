# app/logging_config.py

"""
Sistema de logging profesional para JAGI ERP.

Características:
- Rotación automática de archivos (diario)
- Logs estructurados con contexto
- Diferentes handlers según nivel
- Colores en consola para desarrollo
- Compatible con herramientas de análisis (ELK, Datadog)

Inspirado en:
- Python Logging Cookbook
- 12-Factor App methodology

Autor: Jonatan Corrales
Fecha: Enero 2026
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any

from app.config import settings


# ==========================================
# CONFIGURACIÓN DE DIRECTORIOS
# ==========================================

# Directorio base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Crear directorio de logs si no existe
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Rutas de archivos de log
APP_LOG_FILE = LOGS_DIR / "app.log"
ERROR_LOG_FILE = LOGS_DIR / "errors.log"


# ==========================================
# FORMATOS DE LOG
# ==========================================

# Formato detallado para archivos
DETAILED_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | "
    "%(funcName)s:%(lineno)d | %(message)s"
)

# Formato simple para consola
CONSOLE_FORMAT = "%(levelname)s:%(name)s:%(message)s"

# Formato de fecha
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ==========================================
# COLORES PARA CONSOLA (Solo desarrollo)
# ==========================================

class ColoredFormatter(logging.Formatter):
    """
    Formateador que agrega colores a los logs en consola.
    Solo se usa en desarrollo para mejor legibilidad.
    """
    
    # Códigos ANSI para colores
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[1;31m', # Bold Red
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatea el log con colores según el nivel."""
        # Agregar color al nivel
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{levelname}{self.RESET}"
            )
        
        return super().format(record)


# ==========================================
# FILTROS PERSONALIZADOS
# ==========================================

class ErrorFilter(logging.Filter):
    """
    Filtro que solo deja pasar logs de nivel ERROR o superior.
    Se usa para el archivo errors.log
    """
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= logging.ERROR


# ==========================================
# CONFIGURACIÓN DE HANDLERS
# ==========================================

def get_console_handler() -> logging.Handler:
    """
    Handler para salida en consola (terminal).
    Usa colores en desarrollo, simple en producción.
    """
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Usar colores solo en desarrollo
    if settings.app.environment == "development":
        formatter = ColoredFormatter(
            fmt=CONSOLE_FORMAT,
            datefmt=DATE_FORMAT
        )
    else:
        formatter = logging.Formatter(
            fmt=CONSOLE_FORMAT,
            datefmt=DATE_FORMAT
        )
    
    console_handler.setFormatter(formatter)
    return console_handler


def get_file_handler() -> logging.Handler:
    """
    Handler para archivo de logs general (app.log).
    
    Características:
    - Rotación diaria a medianoche
    - Mantiene últimos 30 días
    - Formato detallado con timestamp, módulo, función, línea
    """
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=APP_LOG_FILE,
        when="midnight",         # Rotar a medianoche
        interval=1,              # Cada 1 día
        backupCount=30,          # Mantener 30 archivos
        encoding="utf-8",
        delay=False
    )
    
    # Formato del nombre de archivos rotados
    file_handler.suffix = "%Y-%m-%d"
    
    formatter = logging.Formatter(
        fmt=DETAILED_FORMAT,
        datefmt=DATE_FORMAT
    )
    file_handler.setFormatter(formatter)
    
    return file_handler


def get_error_file_handler() -> logging.Handler:
    """
    Handler para archivo de errores (errors.log).
    
    Solo registra ERROR y CRITICAL.
    Útil para análisis rápido de problemas.
    """
    error_handler = logging.handlers.TimedRotatingFileHandler(
        filename=ERROR_LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=90,          # Mantener errores por 90 días
        encoding="utf-8",
        delay=False
    )
    
    error_handler.suffix = "%Y-%m-%d"
    error_handler.addFilter(ErrorFilter())  # Solo errores
    
    formatter = logging.Formatter(
        fmt=DETAILED_FORMAT,
        datefmt=DATE_FORMAT
    )
    error_handler.setFormatter(formatter)
    
    return error_handler


# ==========================================
# CONFIGURACIÓN DEL LOGGER ROOT
# ==========================================

def setup_logging() -> None:
    """
    Configura el sistema de logging de la aplicación.
    
    Se ejecuta UNA SOLA VEZ al iniciar la app.
    Configura:
    - Logger root con nivel según entorno
    - Handler de consola (con colores en desarrollo)
    - Handler de archivo general
    - Handler de archivo de errores
    """
    
    # Obtener logger root
    root_logger = logging.getLogger()
    
    # Establecer nivel según entorno
    log_level = getattr(logging, settings.app.log_level.upper())
    root_logger.setLevel(log_level)
    
    # Limpiar handlers existentes (por si se ejecuta dos veces)
    root_logger.handlers.clear()
    
    # Agregar handlers
    root_logger.addHandler(get_console_handler())
    root_logger.addHandler(get_file_handler())
    root_logger.addHandler(get_error_file_handler())
    
    # Prevenir que logs se propaguen al root de Python
    root_logger.propagate = False
    
    # Log inicial de sistema
    logger = logging.getLogger(__name__)
    logger.info(
        f"Sistema de logging inicializado | "
        f"Entorno: {settings.app.environment} | "
        f"Nivel: {settings.app.log_level}"
    )
    logger.debug(f"Logs guardados en: {LOGS_DIR}")


# ==========================================
# HELPERS PARA LOGGING ESTRUCTURADO
# ==========================================

def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any
) -> None:
    """
    Helper para logging estructurado con contexto adicional.
    
    Args:
        logger: Logger a usar
        level: Nivel de log (logging.INFO, logging.ERROR, etc.)
        message: Mensaje principal
        **context: Pares clave-valor de contexto adicional
        
    Ejemplo:
        log_with_context(
            logger,
            logging.INFO,
            "Usuario creado",
            user_id=123,
            email="user@example.com",
            source="registration_form"
        )
    """
    # Formatear contexto como JSON-like
    if context:
        context_str = " | ".join(f"{k}={v}" for k, v in context.items())
        full_message = f"{message} | {context_str}"
    else:
        full_message = message
    
    logger.log(level, full_message)


# ==========================================
# DECORADOR PARA LOGGING AUTOMÁTICO
# ==========================================

import functools
from typing import Callable


def log_execution(logger: logging.Logger):
    """
    Decorador para loguear automáticamente la ejecución de funciones.
    
    Uso:
        @log_execution(logger)
        def procesar_pedido(pedido_id):
            ...
    
    Logs generados:
    - INFO al iniciar función
    - INFO al terminar exitosamente (con tiempo)
    - ERROR si hay excepción
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            func_name = func.__name__
            
            # Log de inicio
            logger.debug(f"Ejecutando {func_name}")
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Log de éxito
                elapsed = time.time() - start_time
                logger.debug(
                    f"Completado {func_name} | "
                    f"Tiempo: {elapsed:.3f}s"
                )
                
                return result
                
            except Exception as e:
                # Log de error
                elapsed = time.time() - start_time
                logger.error(
                    f"Error en {func_name} | "
                    f"Tiempo: {elapsed:.3f}s | "
                    f"Error: {str(e)}",
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator