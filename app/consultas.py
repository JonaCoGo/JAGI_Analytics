# consultas.py

import pandas as pd
from datetime import datetime, timedelta
from app.services.analisis_marca_service import get_analisis_marca
from app.services.producto_service import get_consulta_producto
from app.services.existencias_service import get_existencias_por_tienda
from app.services.movimiento_service import get_movimiento, get_resumen_movimiento
from app.services.faltantes_service import get_faltantes
from app.services.reabastecimiento_service import get_reabastecimiento_avanzado
from app.services.redistribucion_service import get_redistribucion_regional
from app.database import (get_connection, date_subtract_days, date_format_convert,
    current_date, DB_TYPE, DATA_DIR
)

DB_NAME = "jagi_mahalo.db"
