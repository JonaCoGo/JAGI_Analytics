# app/exceptions.py

"""
Excepciones personalizadas para JAGI ERP.

Jerarquía de excepciones siguiendo mejores prácticas:
- Todas heredan de BaseAppException
- Agrupadas por dominio (Database, Validation, Business)
- Incluyen contexto adicional (códigos de error, datos)

Inspirado en:
- Django exceptions
- FastAPI HTTPException
- Flask abort patterns

"""

from typing import Any, Optional, Dict


# ==========================================
# EXCEPCIÓN BASE
# ==========================================

class BaseAppException(Exception):
    """
    Excepción base para todas las excepciones del ERP.
    
    Todas las excepciones personalizadas deben heredar de esta clase.
    Permite captura global y logging consistente.
    """
    
    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Args:
            message: Mensaje de error legible para humanos
            code: Código de error único (para APIs/logging)
            status_code: Código HTTP apropiado
            details: Información adicional del error
        """
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la excepción a diccionario para respuestas API."""
        return {
            "error": True,
            "code": self.code,
            "message": self.message,
            "details": self.details
        }


# ==========================================
# EXCEPCIONES DE BASE DE DATOS
# ==========================================

class DatabaseException(BaseAppException):
    """Excepción base para errores de base de datos."""
    
    def __init__(
        self,
        message: str,
        code: str = "DATABASE_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=500,
            details=details
        )


class ConnectionError(DatabaseException):
    """Error al conectar con la base de datos."""
    
    def __init__(self, message: str = "No se pudo conectar a la base de datos"):
        super().__init__(
            message=message,
            code="DB_CONNECTION_ERROR"
        )


class QueryError(DatabaseException):
    """Error al ejecutar una consulta SQL."""
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        params: Optional[Dict] = None
    ):
        details = {}
        if query:
            details["query"] = query
        if params:
            details["params"] = params
        
        super().__init__(
            message=message,
            code="DB_QUERY_ERROR",
            details=details
        )


class TransactionError(DatabaseException):
    """Error durante una transacción de base de datos."""
    
    def __init__(self, message: str = "Error en transacción de base de datos"):
        super().__init__(
            message=message,
            code="DB_TRANSACTION_ERROR"
        )


# ==========================================
# EXCEPCIONES DE VALIDACIÓN
# ==========================================

class ValidationException(BaseAppException):
    """Excepción base para errores de validación de datos."""
    
    def __init__(
        self,
        message: str,
        code: str = "VALIDATION_ERROR",
        field: Optional[str] = None,
        value: Any = None
    ):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        
        super().__init__(
            message=message,
            code=code,
            status_code=400,
            details=details
        )


class InvalidDataError(ValidationException):
    """Datos inválidos o mal formateados."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None
    ):
        super().__init__(
            message=message,
            code="INVALID_DATA",
            field=field,
            value=value
        )


class MissingFieldError(ValidationException):
    """Campo requerido faltante."""
    
    def __init__(self, field: str):
        super().__init__(
            message=f"El campo '{field}' es requerido",
            code="MISSING_FIELD",
            field=field
        )


class DuplicateEntryError(ValidationException):
    """Intento de crear entrada duplicada."""
    
    def __init__(
        self,
        message: str = "Ya existe un registro con estos datos",
        field: Optional[str] = None,
        value: Any = None
    ):
        super().__init__(
            message=message,
            code="DUPLICATE_ENTRY",
            field=field,
            value=value
        )


# ==========================================
# EXCEPCIONES DE LÓGICA DE NEGOCIO
# ==========================================

class BusinessLogicException(BaseAppException):
    """Excepción base para errores de lógica de negocio."""
    
    def __init__(
        self,
        message: str,
        code: str = "BUSINESS_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=422,  # Unprocessable Entity
            details=details
        )


class ProductNotFoundError(BusinessLogicException):
    """Producto no encontrado en la base de datos."""
    
    def __init__(self, product_id: Any):
        super().__init__(
            message=f"Producto '{product_id}' no encontrado",
            code="PRODUCT_NOT_FOUND",
            details={"product_id": str(product_id)}
        )


class InsufficientStockError(BusinessLogicException):
    """Stock insuficiente para realizar la operación."""
    
    def __init__(
        self,
        product_id: Any,
        required: int,
        available: int
    ):
        super().__init__(
            message=f"Stock insuficiente para producto '{product_id}'",
            code="INSUFFICIENT_STOCK",
            details={
                "product_id": str(product_id),
                "required": required,
                "available": available
            }
        )


class InvalidDateRangeError(BusinessLogicException):
    """Rango de fechas inválido."""
    
    def __init__(self, start_date: str, end_date: str):
        super().__init__(
            message="La fecha inicial debe ser menor que la fecha final",
            code="INVALID_DATE_RANGE",
            details={
                "start_date": start_date,
                "end_date": end_date
            }
        )


class StoreNotFoundError(BusinessLogicException):
    """Tienda no encontrada."""
    
    def __init__(self, store_id: Any):
        super().__init__(
            message=f"Tienda '{store_id}' no encontrada",
            code="STORE_NOT_FOUND",
            details={"store_id": str(store_id)}
        )


# ==========================================
# EXCEPCIONES DE ARCHIVO/EXPORTACIÓN
# ==========================================

class FileException(BaseAppException):
    """Excepción base para errores de archivos."""
    
    def __init__(
        self,
        message: str,
        code: str = "FILE_ERROR",
        filename: Optional[str] = None
    ):
        details = {}
        if filename:
            details["filename"] = filename
        
        super().__init__(
            message=message,
            code=code,
            status_code=500,
            details=details
        )


class FileNotFoundError(FileException):
    """Archivo no encontrado."""
    
    def __init__(self, filename: str):
        super().__init__(
            message=f"Archivo '{filename}' no encontrado",
            code="FILE_NOT_FOUND",
            filename=filename
        )


class FileGenerationError(FileException):
    """Error al generar archivo (Excel, PDF, etc.)."""
    
    def __init__(self, message: str, filename: Optional[str] = None):
        super().__init__(
            message=message,
            code="FILE_GENERATION_ERROR",
            filename=filename
        )


# ==========================================
# EXCEPCIONES DE AUTENTICACIÓN/AUTORIZACIÓN
# ==========================================

class AuthException(BaseAppException):
    """Excepción base para errores de autenticación/autorización."""
    
    def __init__(
        self,
        message: str,
        code: str = "AUTH_ERROR"
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=401
        )


class UnauthorizedError(AuthException):
    """Usuario no autenticado."""
    
    def __init__(self, message: str = "Autenticación requerida"):
        super().__init__(
            message=message,
            code="UNAUTHORIZED"
        )


class ForbiddenError(AuthException):
    """Usuario autenticado pero sin permisos."""
    
    def __init__(self, message: str = "No tienes permisos para esta acción"):
        super().__init__(
            message=message,
            code="FORBIDDEN"
        )
        self.status_code = 403


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_exception_by_code(code: str) -> type:
    """
    Obtiene la clase de excepción por su código.
    
    Útil para deserializar errores desde logs o APIs.
    
    Args:
        code: Código de error (ej: "PRODUCT_NOT_FOUND")
        
    Returns:
        Clase de excepción correspondiente o BaseAppException
    """
    exceptions_map = {
        "DB_CONNECTION_ERROR": ConnectionError,
        "DB_QUERY_ERROR": QueryError,
        "DB_TRANSACTION_ERROR": TransactionError,
        "INVALID_DATA": InvalidDataError,
        "MISSING_FIELD": MissingFieldError,
        "DUPLICATE_ENTRY": DuplicateEntryError,
        "PRODUCT_NOT_FOUND": ProductNotFoundError,
        "INSUFFICIENT_STOCK": InsufficientStockError,
        "INVALID_DATE_RANGE": InvalidDateRangeError,
        "STORE_NOT_FOUND": StoreNotFoundError,
        "FILE_NOT_FOUND": FileNotFoundError,
        "FILE_GENERATION_ERROR": FileGenerationError,
        "UNAUTHORIZED": UnauthorizedError,
        "FORBIDDEN": ForbiddenError,
    }
    
    return exceptions_map.get(code, BaseAppException)