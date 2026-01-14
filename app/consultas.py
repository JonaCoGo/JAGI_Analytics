# consultas.py

import sqlite3
import os
import pandas as pd
import unicodedata
from datetime import datetime, timedelta
from app.services.analisis_marca_service import get_analisis_marca
from app.services.producto_service import get_consulta_producto
from app.services.existencias_service import get_existencias_por_tienda
from app.services.movimiento_service import get_movimiento, get_resumen_movimiento
from app.services.faltantes_service import get_faltantes
from app.services.reabastecimiento_service import get_reabastecimiento_avanzado
from app.database import (
    get_connection,
    date_subtract_days,
    date_format_convert,
    current_date,
    DB_TYPE,
    DATA_DIR
)

DB_NAME = "jagi_mahalo.db"

#------------------------------------------------------ REDISTRIBUCION REGIONAL ------------------------------------------------------#

def get_redistribucion_regional(dias=30, ventas_min=1, tienda_origen=None):
    """
    Sugiere redistribución regional (opcional: desde una tienda origen específica).
    - Usa config_tiendas en lugar de map_tiendas, map_regiones y tiendas_fijas.
    - Analiza ventas recientes (últimos `dias`) y existencias actuales.
    - Respeta stock mínimo por tipo/marca y referencias fijas.
    - Devuelve un DataFrame con resultados y genera redistribucion_regional.xlsx
    """

    with get_connection() as conn:
        # Configuraciones de stock mínimo
        df_cfg = pd.read_sql("SELECT tipo, cantidad FROM stock_minimo_config", conn)
        cfg_map = {str(r["tipo"]).lower(): int(r["cantidad"]) for _, r in df_cfg.iterrows() if pd.notna(r["cantidad"])}

        # Tablas auxiliares
        referencias_fijas = pd.read_sql("SELECT cod_barras FROM referencias_fijas", conn)["cod_barras"].dropna().astype(str).tolist()
        marcas_multimarca = pd.read_sql("SELECT marca FROM marcas_multimarca", conn)["marca"].dropna().astype(str).tolist()
        codigos_excluidos = pd.read_sql("SELECT cod_barras FROM codigos_excluidos", conn)["cod_barras"].dropna().astype(str).tolist()

        # 🔹 Nueva tabla unificada
        config_tiendas = pd.read_sql("SELECT raw_name, clean_name, region, fija, tipo_tienda FROM config_tiendas", conn)

        #✅ Usar funciones helper para fechas
        fecha_desde = date_subtract_days(dias)
        fecha_col = date_format_convert('h.f_sistema')

        # Ventas recientes
        ventas = pd.read_sql_query(f"""
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

        # Existencias actuales
        existencias = pd.read_sql_query("""
            SELECT
                COALESCE(ct.clean_name, s.d_almacen) AS tienda_clean,
                s.d_almacen AS tienda_raw,
                s.c_barra,
                s.d_marca,
                s.saldo_disponible AS stock_actual
            FROM ventas_saldos_raw s
            LEFT JOIN config_tiendas ct ON s.d_almacen = ct.raw_name
        """, conn)

    # --- Normalización y región ---
    config_tiendas["raw_norm"] = config_tiendas["raw_name"].fillna("").apply(_norm)
    config_tiendas["clean_norm"] = config_tiendas["clean_name"].fillna("").apply(_norm)
    region_map = dict(zip(config_tiendas["clean_norm"], config_tiendas["region"]))
    fija_set = set(config_tiendas.loc[config_tiendas["fija"] == 1, "clean_name"].apply(_norm))

    # Normalizar ventas y existencias
    for df_x in (ventas, existencias):
        df_x["tienda_clean"] = df_x["tienda_clean"].fillna("").astype(str)
        df_x["tienda_norm"] = df_x["tienda_clean"].apply(_norm)
        df_x["region"] = df_x["tienda_norm"].map(region_map).fillna("SIN REGION")
        if "ventas_periodo" in df_x.columns:
            df_x["ventas_periodo"] = pd.to_numeric(df_x["ventas_periodo"], errors="coerce").fillna(0)

    # --- Stock mínimo dinámico ---
    ref_set = set([r.strip().upper() for r in referencias_fijas if r])
    marca_set = set([m.strip().upper() for m in marcas_multimarca if m])

    def calcular_stock_min(c_barra, d_marca, tienda_clean_norm):
        c = (str(c_barra) or "").upper()
        m = (str(d_marca) or "").upper()

        if c in ref_set:
            return cfg_map.get("fijo_especial", cfg_map.get("fijo_normal", 5))
        if m in marca_set:
            return cfg_map.get("multimarca", 2)
        if "JGL" in c or "JGL" in m:
            return cfg_map.get("jgl", 3)
        if "JGM" in c or "JGM" in m:
            return cfg_map.get("jgm", 3)
        return cfg_map.get("general", 4)

    existencias["stock_minimo"] = existencias.apply(
        lambda r: calcular_stock_min(r["c_barra"], r["d_marca"], r["tienda_norm"]), axis=1
    )

    # --- Unir existencias y ventas ---
    ventas_agg = ventas.groupby(["tienda_norm", "c_barra", "d_marca"], as_index=False)["ventas_periodo"].sum()
    df = pd.merge(
        existencias,
        ventas_agg,
        on=["tienda_norm", "c_barra", "d_marca"],
        how="left"
    ).fillna({"ventas_periodo": 0})

    df["stock_actual"] = pd.to_numeric(df["stock_actual"], errors="coerce").fillna(0).astype(int)
    df["ventas_periodo"] = df["ventas_periodo"].astype(int)
    df["region"] = df["tienda_norm"].map(region_map).fillna("SIN REGION")

    # --- Detectar orígenes (sobrestock) y destinos (faltantes) ---
    origen = df[(df["stock_actual"] > df["stock_minimo"]) & (df["ventas_periodo"] == 0)].copy()
    origen = origen[~origen["tienda_norm"].isin(fija_set)]  # excluir tiendas fijas

    destino = df[(df["stock_actual"] < df["stock_minimo"]) & (df["ventas_periodo"] >= ventas_min)].copy()

    # --- Si se indica tienda origen específica ---
    if tienda_origen:
        tienda_origen_norm = _norm(tienda_origen)
        if tienda_origen_norm not in origen["tienda_norm"].values:
            print(f"⚠️ No hay sobrestock en '{tienda_origen}'.")
            return pd.DataFrame()

        region_obj = origen.loc[origen["tienda_norm"] == tienda_origen_norm, "region"].iloc[0]
        origen = origen[origen["tienda_norm"] == tienda_origen_norm]
        destino = destino[destino["region"] == region_obj]

    n_origen, n_destino = len(origen), len(destino)
    print(f"🔎 Orígenes candidatos: {n_origen}, Destinos candidatos: {n_destino}")

    if origen.empty or destino.empty:
        print("✅ No hay oportunidades de redistribución.")
        return pd.DataFrame()

    # --- Emparejar orígenes y destinos dentro de la región ---
    merged = origen.merge(
        destino,
        on=["region", "c_barra", "d_marca"],
        how="inner",
        suffixes=("_origen", "_destino")
    )

    if merged.empty:
        print("✅ No hay coincidencias origen-destino por referencia.")
        return pd.DataFrame()

    merged["exceso_origen"] = (merged["stock_actual_origen"] - merged["stock_minimo_origen"]).clip(lower=0)
    merged["faltante_destino"] = (merged["stock_minimo_destino"] - merged["stock_actual_destino"]).clip(lower=0)

    merged["cantidad_sugerida"] = merged.apply(
        lambda r: int(max(1, min(int(r["exceso_origen"] // 2), int(r["faltante_destino"])))) if (r["exceso_origen"] > 0 and r["faltante_destino"] > 0) else 0,
        axis=1
    )

    final = merged[merged["cantidad_sugerida"] > 0].copy()

    if final.empty:
        print("✅ No hay movimientos sugeridos.")
        return pd.DataFrame()

    final = final[[
        "region", "c_barra", "d_marca",
        "tienda_clean_origen", "stock_actual_origen", "ventas_periodo_origen",
        "tienda_clean_destino", "stock_actual_destino", "ventas_periodo_destino",
        "stock_minimo_destino", "cantidad_sugerida"
    ]].rename(columns={
        "tienda_clean_origen": "tienda_origen",
        "tienda_clean_destino": "tienda_destino",
        "stock_actual_origen": "stock_origen",
        "stock_actual_destino": "stock_destino",
        "ventas_periodo_origen": "ventas_origen",
        "ventas_periodo_destino": "ventas_destino"
    })

    final = final.sort_values(by=["region", "d_marca", "c_barra", "tienda_origen"])
    final.to_excel("redistribucion_regional.xlsx", index=False)

    print(f"📦 Redistribución generada: {len(final)} movimientos sugeridos.")
    print("📂 Archivo: redistribucion_regional.xlsx")

    return final
