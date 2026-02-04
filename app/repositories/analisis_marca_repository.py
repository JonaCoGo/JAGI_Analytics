# app/repositories/analisis_marca_repository.py

import pandas as pd

def get_top10_marca(conn, marca_norm):
    query = """
    SELECT 
        s.c_barra,
        s.d_marca,
        s.d_color_proveedor AS color,
        SUM(h.cn_venta) AS ventas_30d
    FROM ventas_saldos_raw s
    INNER JOIN ventas_historico_raw h ON s.c_barra = h.c_barra
    WHERE UPPER(s.d_marca) LIKE ?
      AND DATE(substr(h.f_sistema,7,4)||'-'||substr(h.f_sistema,4,2)||'-'||substr(h.f_sistema,1,2)) >= DATE('now', '-30 days')
    GROUP BY s.c_barra, s.d_marca, s.d_color_proveedor
    ORDER BY ventas_30d DESC
    LIMIT 10
    """
    return pd.read_sql(query, conn, params=(f"%{marca_norm}%",))

def get_productos_marca_sin_ventas(conn, marca_norm):
    query = """
    SELECT DISTINCT
        c_barra,
        d_marca,
        d_color_proveedor AS color,
        0 AS ventas_30d
    FROM ventas_saldos_raw
    WHERE UPPER(d_marca) LIKE ?
    LIMIT 10
    """
    return pd.read_sql(query, conn, params=(f"%{marca_norm}%",))

def get_tiendas_configuradas(conn):
    query = """
    SELECT raw_name, clean_name, region
    FROM config_tiendas
    WHERE clean_name NOT LIKE '%BODEGA%'
    """
    return pd.read_sql(query, conn)

def get_stock_por_barra(conn, barra):
    query = """
    SELECT d_almacen, saldo_disponible
    FROM ventas_saldos_raw
    WHERE c_barra = ?
    """
    return pd.read_sql(query, conn, params=(barra,))