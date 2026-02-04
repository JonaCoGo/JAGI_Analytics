# app/repositories/redistribucion_repository.py

import pandas as pd

def fetch_configuracion(conn):
    cfg = pd.read_sql("SELECT tipo, cantidad FROM stock_minimo_config", conn)
    referencias = pd.read_sql(
        "SELECT cod_barras FROM referencias_fijas", conn
    )["cod_barras"].dropna().astype(str).tolist()

    marcas = pd.read_sql(
        "SELECT marca FROM marcas_multimarca", conn
    )["marca"].dropna().astype(str).tolist()

    excluidos = pd.read_sql(
        "SELECT cod_barras FROM codigos_excluidos", conn
    )["cod_barras"].dropna().astype(str).tolist()

    tiendas = pd.read_sql(
        "SELECT raw_name, clean_name, region, fija, tipo_tienda FROM config_tiendas",
        conn
    )

    return cfg, referencias, marcas, excluidos, tiendas


def fetch_ventas(conn, fecha_col, fecha_desde):
    return pd.read_sql_query(f"""
        SELECT
            COALESCE(ct.clean_name, h.d_almacen) AS tienda_clean,
            h.d_almacen AS tienda_raw,
            h.c_barra,
            h.d_marca,
            SUM(h.cn_venta) AS ventas_periodo
        FROM ventas_historico_raw h
        LEFT JOIN config_tiendas ct ON h.d_almacen = ct.raw_name
        WHERE {fecha_col} >= {fecha_desde}
        GROUP BY tienda_clean, h.c_barra, h.d_marca
    """, conn)


def fetch_existencias(conn):
    return pd.read_sql_query("""
        SELECT
            COALESCE(ct.clean_name, s.d_almacen) AS tienda_clean,
            s.d_almacen AS tienda_raw,
            s.c_barra,
            s.d_marca,
            s.saldo_disponible AS stock_actual
        FROM ventas_saldos_raw s
        LEFT JOIN config_tiendas ct ON s.d_almacen = ct.raw_name
    """, conn)