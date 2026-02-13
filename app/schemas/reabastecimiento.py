# app/schemas/reabastecimiento.py

"""
Schemas para el módulo de Reabastecimiento.

Responsabilidades claras:
- Requests: lo que entra por la API
- MotorParams: lo que usa el motor de cálculo
- ExportParams: filtros y presentación (NO cálculo)
- Responses: lo que devuelve la API
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum
from datetime import datetime

from app.schemas.common import ResponseBase


# ============================================================
# ENUMS
# ============================================================

class PrioridadEnum(str, Enum):
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAJA = "BAJA"


# ============================================================
# REQUESTS (API)
# ============================================================

class ReabastecimientoCalculoRequest(BaseModel):
    """
    Request principal para calcular reabastecimiento desde la API.
    """

    dias_venta: int = Field(
        ...,
        ge=1,
        le=90,
        description="Días para calcular promedio de ventas"
    )

    dias_stock: int = Field(
        ...,
        ge=1,
        le=180,
        description="Días de cobertura objetivo"
    )

    fecha_inicio: str = Field(
        ...,
        description="Fecha inicial del período (DD/MM/YYYY)"
    )

    fecha_fin: str = Field(
        ...,
        description="Fecha final del período (DD/MM/YYYY)"
    )

    tiendas: Optional[List[str]] = Field(
        default=None,
        description="Filtro por tiendas"
    )

    productos: Optional[List[str]] = Field(
        default=None,
        description="Filtro por productos"
    )

    incluir_sin_movimiento: bool = Field(
        default=False,
        description="Incluir productos sin movimiento"
    )

    # ---------------- VALIDACIONES ----------------

    @field_validator("fecha_inicio", "fecha_fin")
    def validar_formato_fecha(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Formato de fecha inválido. Use DD/MM/YYYY")
        return v

    @field_validator("fecha_fin")
    def validar_rango_fechas(cls, v, info):
        if "fecha_inicio" in info.data:
            inicio = datetime.strptime(info.data["fecha_inicio"], "%d/%m/%Y")
            fin = datetime.strptime(v, "%d/%m/%Y")
            if fin < inicio:
                raise ValueError("fecha_fin debe ser posterior a fecha_inicio")
        return v

    @field_validator("tiendas", "productos")
    def normalizar_codigos(cls, v):
        if v:
            return [item.strip().upper() for item in v if item.strip()]
        return v

    @field_validator("dias_stock")
    def validar_stock_vs_venta(cls, v, info):
        if "dias_venta" in info.data and v < info.data["dias_venta"]:
            raise ValueError("dias_stock debe ser >= dias_venta")
        return v


# ============================================================
# MOTOR (LÓGICA INTERNA – NO DEPENDE DE FASTAPI)
# ============================================================

class ProductoNuevo(BaseModel):
    c_barra: str
    d_marca: str
    color: Optional[str] = "SIN COLOR"


class ReabastecimientoMotorParams(BaseModel):
    """
    Parámetros usados EXCLUSIVAMENTE por el motor de cálculo.
    Puede usarse desde API, jobs, scripts o tests.
    """

    dias_reab: int = Field(10, ge=1, le=90)
    dias_exp: int = Field(60, ge=1, le=180)

    ventas_min_exp: int = Field(
        3,
        ge=0,
        description="Ventas mínimas para considerar expansión"
    )

    solo_con_ventas: bool = False
    nuevos_codigos: Optional[List[ProductoNuevo]] = None

    excluir_sin_movimiento: bool = True
    incluir_fijos: bool = True
    guardar_debug_csv: bool = False

    @field_validator("dias_exp")
    def validar_exp_vs_reab(cls, v, info):
        if "dias_reab" in info.data and v < info.data["dias_reab"]:
            raise ValueError("dias_exp debe ser >= dias_reab")
        return v


# ============================================================
# EXPORT / PREVIEW (NO ALTERAN CÁLCULO)
# ============================================================

class ReabastecimientoExportParams(ReabastecimientoMotorParams):
    """
    Parámetros adicionales para preview y exportación.
    NO afectan el cálculo del motor.
    """

    columnas_seleccionadas: Optional[List[str]] = None
    tiendas_filtro: Optional[List[str]] = None
    observaciones_filtro: Optional[List[str]] = None
    tipo_formato: Optional[str] = "general"
    excluir_cantidad_cero: Optional[bool] = False
    solo_compra: Optional[bool] = False

# ============================================================
# RESPONSE MODELS
# ============================================================

class ReabastecimientoItem(BaseModel):
    tienda: str
    producto: str
    descripcion: Optional[str] = None
    stock_actual: int
    venta_promedio: float
    dias_stock_actual: float
    necesidad: int
    prioridad: PrioridadEnum


class ReabastecimientoResponse(ResponseBase):
    """
    Respuesta estándar del cálculo de reabastecimiento.
    """

    total_items: int
    items_con_necesidad: int
    total_unidades_necesarias: int

    parametros: ReabastecimientoCalculoRequest

    items: List[ReabastecimientoItem] = []
    resumen_por_tienda: Optional[dict] = None