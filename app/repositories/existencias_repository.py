# app/repositories/existencias_repository.py

import pandas as pd
from app.database import get_connection


def fetch_existencias_por_tienda():
    query = """
    SELECT 
        t.clean_name AS tienda,
        s.c_barra,
        s.d_marca,
        s.saldo_disponible AS stock_actual,
        t.region,
        t.tipo_tienda,
        t.fija
    FROM ventas_saldos_raw s
    LEFT JOIN config_tiendas t ON s.d_almacen = t.raw_name
    ORDER BY t.clean_name, s.d_marca;
    """
    with get_connection() as conn:
        return pd.read_sql(query, conn)