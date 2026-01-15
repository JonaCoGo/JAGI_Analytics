# redistribucion_service.py

import pandas as pd

from app.database import get_connection, date_subtract_days, date_format_convert
from app.repositories import redistribucion_repository as repo
from app.utils.text import _norm


def get_redistribucion_regional(dias=30, ventas_min=1, tienda_origen=None):

    with get_connection() as conn:
        df_cfg, referencias_fijas, marcas_multimarca, codigos_excluidos, config_tiendas = \
            repo.fetch_configuracion(conn)

        fecha_desde = date_subtract_days(dias)
        fecha_col = date_format_convert("h.f_sistema")

        ventas = repo.fetch_ventas(conn, fecha_col, fecha_desde)
        existencias = repo.fetch_existencias(conn)

    # ---------------- NORMALIZACIÓN ----------------
    cfg_map = {
        str(r["tipo"]).lower(): int(r["cantidad"])
        for _, r in df_cfg.iterrows() if pd.notna(r["cantidad"])
    }

    config_tiendas["clean_norm"] = config_tiendas["clean_name"].fillna("").apply(_norm)
    region_map = dict(zip(config_tiendas["clean_norm"], config_tiendas["region"]))
    fija_set = set(
        config_tiendas.loc[config_tiendas["fija"] == 1, "clean_name"]
        .apply(_norm)
    )

    for df in (ventas, existencias):
        df["tienda_norm"] = df["tienda_clean"].fillna("").apply(_norm)
        df["region"] = df["tienda_norm"].map(region_map).fillna("SIN REGION")

    ventas["ventas_periodo"] = ventas["ventas_periodo"].fillna(0).astype(int)
    existencias["stock_actual"] = existencias["stock_actual"].fillna(0).astype(int)

    # ---------------- STOCK MÍNIMO ----------------
    ref_set = set(r.upper() for r in referencias_fijas)
    marca_set = set(m.upper() for m in marcas_multimarca)

    def stock_min(c, m):
        c, m = str(c).upper(), str(m).upper()
        if c in ref_set:
            return cfg_map.get("fijo_normal", 5)
        if m in marca_set:
            return cfg_map.get("multimarca", 2)
        if "JGL" in c or "JGL" in m:
            return cfg_map.get("jgl", 3)
        if "JGM" in c or "JGM" in m:
            return cfg_map.get("jgm", 3)
        return cfg_map.get("general", 4)

    existencias["stock_minimo"] = existencias.apply(
        lambda r: stock_min(r["c_barra"], r["d_marca"]), axis=1
    )

    # ---------------- MERGE ----------------
    ventas_agg = ventas.groupby(
        ["tienda_norm", "c_barra", "d_marca"],
        as_index=False
    )["ventas_periodo"].sum()

    df = existencias.merge(
        ventas_agg,
        on=["tienda_norm", "c_barra", "d_marca"],
        how="left"
    ).fillna({"ventas_periodo": 0})

    # ---------------- ORIGEN / DESTINO ----------------
    origen = df[
        (df["stock_actual"] > df["stock_minimo"]) &
        (df["ventas_periodo"] == 0) &
        (~df["tienda_norm"].isin(fija_set))
    ]

    destino = df[
        (df["stock_actual"] < df["stock_minimo"]) &
        (df["ventas_periodo"] >= ventas_min)
    ]

    if tienda_origen:
        t_norm = _norm(tienda_origen)
        origen = origen[origen["tienda_norm"] == t_norm]
        if origen.empty:
            return pd.DataFrame()
        region = origen.iloc[0]["region"]
        destino = destino[destino["region"] == region]

    # ---------------- MATCH ----------------
    merged = origen.merge(
        destino,
        on=["region", "c_barra", "d_marca"],
        suffixes=("_origen", "_destino")
    )

    if merged.empty:
        return pd.DataFrame()

    merged["cantidad_sugerida"] = merged.apply(
        lambda r: max(
            1,
            min(
                (r["stock_actual_origen"] - r["stock_minimo_origen"]) // 2,
                (r["stock_minimo_destino"] - r["stock_actual_destino"])
            )
        ),
        axis=1
    )

    final = merged[merged["cantidad_sugerida"] > 0].copy()

    if final.empty:
        return pd.DataFrame()

    return final[[
        "region", "c_barra", "d_marca",
        "tienda_clean_origen", "tienda_clean_destino",
        "cantidad_sugerida"
    ]].rename(columns={
        "tienda_clean_origen": "tienda_origen",
        "tienda_clean_destino": "tienda_destino"
    })