# app/middleware.py

"""
Middleware para manejo global de excepciones en FastAPI.

Este middleware captura todas las excepciones de la aplicación,
las loguea apropiadamente y retorna respuestas JSON estructuradas.

Inspirado en:
- Django REST Framework exception handling
- Flask error handlers
- Express.js error middleware

"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback
from typing import Union

from app.exceptions import BaseAppException

# Logger para este módulo
logger = logging.getLogger(__name__)


# ==========================================
# MIDDLEWARE DE EXCEPCIONES
# ==========================================

async def exception_handler_middleware(request: Request, call_next):
    """
    Middleware que captura todas las excepciones no manejadas.
    
    Flujo:
    1. Intenta ejecutar el request
    2. Si hay excepción, la captura
    3. Loguea con el nivel apropiado
    4. Retorna respuesta JSON estructurada
    
    Args:
        request: Request de FastAPI
        call_next: Siguiente middleware/handler
        
    Returns:
        Response (normal o error)
    """
    try:
        response = await call_next(request)
        return response
        
    except BaseAppException as exc:
        # Excepciones personalizadas de la aplicación
        return handle_app_exception(exc, request)
        
    except RequestValidationError as exc:
        # Errores de validación de Pydantic/FastAPI
        return handle_validation_error(exc, request)
        
    except StarletteHTTPException as exc:
        # Excepciones HTTP de Starlette
        return handle_http_exception(exc, request)
        
    except Exception as exc:
        # Cualquier otra excepción no manejada
        return handle_unexpected_exception(exc, request)


# ==========================================
# HANDLERS ESPECÍFICOS POR TIPO
# ==========================================

def handle_app_exception(
    exc: BaseAppException,
    request: Request
) -> JSONResponse:
    """
    Maneja excepciones personalizadas de la aplicación.
    
    Estas son las que creamos en exceptions.py
    """
    # Log según severidad del error
    if exc.status_code >= 500:
        # Errores de servidor (500+) son ERROR
        logger.error(
            f"Error en {request.method} {request.url.path} | "
            f"Código: {exc.code} | "
            f"Mensaje: {exc.message} | "
            f"Detalles: {exc.details}",
            exc_info=True
        )
    elif exc.status_code >= 400:
        # Errores de cliente (400-499) son WARNING
        logger.warning(
            f"Error de cliente en {request.method} {request.url.path} | "
            f"Código: {exc.code} | "
            f"Mensaje: {exc.message}"
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


def handle_validation_error(
    exc: RequestValidationError,
    request: Request
) -> JSONResponse:
    """
    Maneja errores de validación de Pydantic.
    
    Ocurren cuando los datos enviados no cumplen el schema.
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"Error de validación en {request.method} {request.url.path} | "
        f"Errores: {len(errors)}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "code": "VALIDATION_ERROR",
            "message": "Los datos enviados no son válidos",
            "errors": errors
        }
    )


def handle_http_exception(
    exc: StarletteHTTPException,
    request: Request
) -> JSONResponse:
    """
    Maneja excepciones HTTP estándar (404, 405, etc.).
    """
    logger.info(
        f"HTTP {exc.status_code} en {request.method} {request.url.path}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail
        }
    )


def handle_unexpected_exception(
    exc: Exception,
    request: Request
) -> JSONResponse:
    """
    Maneja excepciones inesperadas (bugs no capturados).
    
    Estos son los más críticos porque indican bugs en el código.
    """
    # Log completo con stack trace
    logger.critical(
        f"❌ EXCEPCIÓN NO MANEJADA en {request.method} {request.url.path} | "
        f"Tipo: {type(exc).__name__} | "
        f"Mensaje: {str(exc)}",
        exc_info=True
    )
    
    # En producción, NO exponer detalles internos
    from app.config import settings
    
    if settings.app.environment == "production":
        message = "Error interno del servidor. Por favor contacta al administrador."
        details = {}
    else:
        # En desarrollo, mostrar detalles para debugging
        message = f"{type(exc).__name__}: {str(exc)}"
        details = {
            "traceback": traceback.format_exc()
        }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "code": "INTERNAL_SERVER_ERROR",
            "message": message,
            "details": details
        }
    )


# ==========================================
# EXCEPTION HANDLERS PARA FastAPI
# ==========================================

async def base_app_exception_handler(
    request: Request,
    exc: BaseAppException
) -> JSONResponse:
    """Handler específico para BaseAppException."""
    return handle_app_exception(exc, request)


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handler específico para RequestValidationError."""
    return handle_validation_error(exc, request)


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """Handler específico para StarletteHTTPException."""
    return handle_http_exception(exc, request)


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handler para cualquier excepción no capturada."""
    return handle_unexpected_exception(exc, request)