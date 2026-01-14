# reabastecimiento_service.py

import pandas as pd

from app.database import get_connection, date_subtract_days, date_format_convert
from app.repositories import reabastecimiento_repository as repo
from app.utils.text import _norm


def get_reabastecimiento_avanzado(
    dias_reab=10,
    dias_exp=60,
    ventas_min_exp=3,
    excluir_sin_movimiento=True,
    incluir_fijos=True,
    guardar_debug_csv=True,
    nuevos_codigos=None,
    solo_con_ventas=False
):
    if nuevos_codigos is None:
        nuevos_codigos = []

    # ---------- CARGA DE DATOS ----------
    with get_connection() as conn:
        cfg_df = repo.fetch_stock_minimo_config(conn)
        referencias_fijas = repo.fetch_referencias_fijas(conn)["cod_barras"].dropna().astype(str).tolist()
        marcas_multimarca = repo.fetch_marcas_multimarca(conn)["marca"].dropna().astype(str).tolist()
        codigos_excluidos = repo.fetch_codigos_excluidos(conn)["cod_barras"].dropna().astype(str).tolist()
        config_tiendas = repo.fetch_config_tiendas(conn)

        fecha_col = date_format_convert("h.f_sistema")
        df = repo.fetch_base_reabastecimiento(
            conn, fecha_col, date_subtract_days(dias_reab)
        )
        df_exp = repo.fetch_ventas_expansion(
            conn, fecha_col, date_subtract_days(dias_exp)
        )

        info_ref = repo.fetch_info_referencias(conn)
        df_existencias = repo.fetch_existencias(conn)

    # ---------- NORMALIZACIÓN ----------
    cfg_map = {
        str(r["tipo"]).lower(): int(r["cantidad"])
        for _, r in cfg_df.iterrows()
        if pd.notna(r["cantidad"])
    }

    config_tiendas["clean_norm"] = config_tiendas["clean_name"].fillna("").apply(_norm)
    region_map = dict(zip(config_tiendas["clean_norm"], config_tiendas["region"]))
    tiendas_fijas = set(
        config_tiendas.loc[config_tiendas["fija"] == 1, "clean_name"].apply(_norm)
    )

    tiendas_all = [
        t for t in config_tiendas["clean_name"].dropna().unique().tolist()
        if "bodega jagi" not in t.lower()
    ]

    ref_set = set(r.upper() for r in referencias_fijas)
    marca_set = set(m.upper() for m in marcas_multimarca)

    df["tienda_norm"] = df["tienda"].fillna("").apply(_norm)
    df["region"] = df["tienda_norm"].map(region_map).fillna("SIN REGION")
    df = df[~df["tienda"].str.contains("bodega jagi", case=False, na=False)]

    # ---------- STOCK MÍNIMO ----------
    def stock_minimo(row):
        tienda = _norm(row["tienda"])
        code = str(row["c_barra"]).upper()
        marca = str(row["d_marca"]).upper()

        if code in ref_set:
            return cfg_map.get("fijo_especial", 8) if tienda in tiendas_fijas else cfg_map.get("fijo_normal", 5)
        if marca in marca_set:
            return cfg_map.get("multimarca", 2)
        if "JGL" in code or "JGL" in marca:
            return cfg_map.get("jgl", 3)
        if "JGM" in code or "JGM" in marca:
            return cfg_map.get("jgm", 3)
        return cfg_map.get("default", 4)

    df["stock_minimo_dinamico"] = df.apply(stock_minimo, axis=1)

    # ---------- DESPACHO ----------
    df["cantidad_a_despachar"] = df.apply(
        lambda r: max(r["stock_minimo_dinamico"] - (r["stock_actual"] or 0), 0)
        if (r["ventas_periodo"] > 0 or str(r["c_barra"]).upper() in ref_set)
        else 0,
        axis=1
    )

    df["observacion"] = df.apply(
        lambda r: "OK"
        if r["cantidad_a_despachar"] == 0
        else "COMPRA"
        if r["cantidad_a_despachar"] > (r["stock_bodega"] or 0)
        else "REABASTECER",
        axis=1
    )

    if excluir_sin_movimiento:
        df = df[(df["ventas_periodo"] > 0) | (df["c_barra"].str.upper().isin(ref_set))]

    # ---------- LIMPIEZA FINAL ----------
    df = df[df["observacion"] != "OK"]
    df = df.sort_values(by=["region", "tienda", "d_marca", "c_barra"])

    columnas = [
        "region", "tienda", "c_barra", "d_marca", "color",
        "ventas_periodo", "stock_actual", "stock_bodega",
        "stock_minimo_dinamico", "cantidad_a_despachar", "observacion"
    ]

    result = df[columnas].copy()

    if guardar_debug_csv:
        sin_region = df[df["region"] == "SIN REGION"][["tienda"]].drop_duplicates()
        if not sin_region.empty:
            sin_region.to_csv("tiendas_sin_region.csv", index=False, encoding="utf-8-sig")

    if solo_con_ventas:
        result = result[
            (result["ventas_periodo"] > 0)
            | (result["observacion"].isin(["EXPANSION", "NUEVO"]))
        ]

    return result