# app/services/reabastecimiento_service.py

import pandas as pd
from app.database import get_connection, date_subtract_days, date_format_convert
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

    # =========================
    # CARGA BASE DE DATOS
    # =========================
    with get_connection() as conn:

        df_cfg = pd.read_sql("SELECT tipo, cantidad FROM stock_minimo_config", conn)
        cfg_map = {
            str(r["tipo"]).lower(): int(r["cantidad"])
            for _, r in df_cfg.iterrows()
            if pd.notna(r["cantidad"])
        }

        referencias_fijas = pd.read_sql(
            "SELECT cod_barras FROM referencias_fijas", conn
        )["cod_barras"].dropna().astype(str).tolist()

        marcas_multimarca = pd.read_sql(
            "SELECT marca FROM marcas_multimarca", conn
        )["marca"].dropna().astype(str).tolist()

        codigos_excluidos = pd.read_sql(
            "SELECT cod_barras FROM codigos_excluidos", conn
        )["cod_barras"].dropna().astype(str).tolist()

        config_tiendas = pd.read_sql(
            "SELECT raw_name, clean_name, region, fija, tipo_tienda FROM config_tiendas",
            conn
        )

        # -------------------------
        # STOCK TOTAL REAL DE BODEGA (CLAVE)
        # -------------------------
        df_bodega_total = pd.read_sql("""
            SELECT 
                c_barra,
                SUM(saldo_disponibles) AS stock_bodega_total
            FROM inventario_bodega_raw
            GROUP BY c_barra
        """, conn)

        df_bodega_total["c_barra"] = (
            df_bodega_total["c_barra"]
            .astype(str)
            .str.upper()
        )

        stock_bodega_map = dict(
            zip(
                df_bodega_total["c_barra"],
                df_bodega_total["stock_bodega_total"]
            )
        )

        # -------------------------
        # REABASTECIMIENTO BASE
        # -------------------------
        fecha_desde_reab = date_subtract_days(dias_reab)
        fecha_col = date_format_convert("h.f_sistema")

        query = f"""
        WITH base AS (
            SELECT 
                s.c_barra,
                s.d_marca,
                COALESCE(ct.clean_name, s.d_almacen) AS tienda,
                s.d_color_proveedor AS color,
                s.saldo_disponible AS stock_actual,
                COALESCE(b.saldo_disponibles, 0) AS stock_bodega
            FROM ventas_saldos_raw s
            LEFT JOIN inventario_bodega_raw b ON s.c_barra = b.c_barra
            LEFT JOIN config_tiendas ct ON s.d_almacen = ct.raw_name
            WHERE s.c_barra NOT IN (SELECT cod_barras FROM codigos_excluidos)
        ),
        ventas_reab AS (
            SELECT 
                h.c_barra,
                COALESCE(ct.clean_name, h.d_almacen) AS tienda,
                SUM(h.cn_venta) AS ventas_periodo
            FROM ventas_historico_raw h
            LEFT JOIN config_tiendas ct ON h.d_almacen = ct.raw_name
            WHERE {fecha_col} >= {fecha_desde_reab}
            GROUP BY h.c_barra, tienda
        )
        SELECT 
            base.c_barra,
            base.d_marca,
            base.tienda,
            base.color,
            base.stock_actual,
            base.stock_bodega,
            COALESCE(v.ventas_periodo, 0) AS ventas_periodo
        FROM base
        LEFT JOIN ventas_reab v
            ON base.c_barra = v.c_barra AND base.tienda = v.tienda;
        """
        df = pd.read_sql(query, conn)

        # -------------------------
        # EXPANSIÓN (VENTAS LARGAS)
        # -------------------------
        fecha_desde_exp = date_subtract_days(dias_exp)

        query_exp = f"""
        SELECT 
            h.c_barra,
            COALESCE(ct.clean_name, h.d_almacen) AS tienda,
            SUM(h.cn_venta) AS ventas_expansion
        FROM ventas_historico_raw h
        LEFT JOIN config_tiendas ct ON h.d_almacen = ct.raw_name
        WHERE {fecha_col} >= {fecha_desde_exp}
        GROUP BY h.c_barra, tienda
        """
        df_exp = pd.read_sql(query_exp, conn)

        tiendas_all = config_tiendas["clean_name"].dropna().unique().tolist()

        info_ref = pd.read_sql("""
            SELECT DISTINCT c_barra, d_marca, d_color_proveedor AS color
            FROM ventas_saldos_raw
            WHERE c_barra IS NOT NULL
        """, conn)

        df_existencias = pd.read_sql("""
            SELECT DISTINCT 
                COALESCE(ct.clean_name, s.d_almacen) AS tienda,
                s.c_barra
            FROM ventas_saldos_raw s
            LEFT JOIN config_tiendas ct ON s.d_almacen = ct.raw_name
        """, conn)

    # =========================
    # NORMALIZACIÓN
    # =========================
    config_tiendas["clean_norm"] = config_tiendas["clean_name"].fillna("").apply(_norm)
    region_map = dict(zip(config_tiendas["clean_norm"], config_tiendas["region"]))

    tiendas_fijas_set = set(
        config_tiendas.loc[config_tiendas["fija"] == 1, "clean_norm"]
    )

    df["tienda_norm"] = df["tienda"].fillna("").apply(_norm)
    df["region"] = df["tienda_norm"].map(region_map).fillna("SIN REGION")

    df = df[~df["tienda"].str.contains("bodega jagi", case=False, na=False)]
    tiendas_all = [t for t in tiendas_all if "bodega jagi" not in t.lower()]

    ref_set = set(r.strip().upper() for r in referencias_fijas if r)
    marca_set = set(m.strip().upper() for m in marcas_multimarca if m)

    # =========================
    # STOCK MÍNIMO DINÁMICO
    # =========================
    def calcular_stock_min(row):
        code = str(row["c_barra"]).upper()
        marca = str(row["d_marca"]).upper()

        if code in ref_set:
            return cfg_map.get(
                "fijo_especial" if row["tienda_norm"] in tiendas_fijas_set else "fijo_normal", 5
            )
        if marca in marca_set:
            return cfg_map.get("multimarca", 2)
        if "JGL" in code or "JGL" in marca:
            return cfg_map.get("jgl", 3)
        if "JGM" in code or "JGM" in marca:
            return cfg_map.get("jgm", 3)
        return cfg_map.get("default", 4)

    df["stock_minimo_dinamico"] = df.apply(calcular_stock_min, axis=1)

    df["cantidad_a_despachar"] = df.apply(
        lambda r: max(r["stock_minimo_dinamico"] - (r["stock_actual"] or 0), 0)
        if (r["ventas_periodo"] > 0 or r["c_barra"].upper() in ref_set)
        else 0,
        axis=1
    )

    # =========================
    # MOTOR DE ASIGNACIÓN REABASTECIMIENTO
    # =========================
    df["es_tienda_fija"] = df["tienda_norm"].isin(tiendas_fijas_set).astype(int)
    df["prioridad_tienda"] = df["es_tienda_fija"] * 100 + df["ventas_periodo"]

    df["cantidad_asignada_real"] = 0
    df["stock_bodega_restante"] = df["stock_bodega"]

    for c_barra, grupo in df.groupby("c_barra"):
        stock = grupo["stock_bodega"].iloc[0]
        grupo_ord = grupo.sort_values("prioridad_tienda", ascending=False)

        for idx, row in grupo_ord.iterrows():
            if stock <= 0:
                break
            demanda = row["cantidad_a_despachar"]
            if demanda <= 0:
                continue

            asignado = min(demanda, stock)
            df.loc[idx, "cantidad_asignada_real"] = asignado
            stock -= asignado

        df.loc[grupo.index, "stock_bodega_restante"] = stock

    # =========================
    # OBSERVACIÓN BASE
    # =========================
    df["observacion"] = df.apply(
        lambda r: "OK"
        if r["cantidad_a_despachar"] == 0
        else "REABASTECER"
        if r["cantidad_asignada_real"] > 0
        else "COMPRA",
        axis=1
    )

    # =========================
    # EXPANSIÓN + NUEVOS (FILAS)
    # =========================
    df_existencias["tienda_norm"] = df_existencias["tienda"].apply(_norm)
    df_existencias["c_barra_up"] = df_existencias["c_barra"].astype(str).str.upper()
    existentes = set(zip(df_existencias["tienda_norm"], df_existencias["c_barra_up"]))

    exp_rows = []

    df_exp_validas = df_exp[
        (df_exp["ventas_expansion"] >= ventas_min_exp)
        & (~df_exp["c_barra"].isin(codigos_excluidos))
    ]

    for _, row in df_exp_validas.iterrows():
        code = row["c_barra"].upper()
        stock_real = stock_bodega_map.get(code, 0)

        info = info_ref[info_ref["c_barra"].astype(str).str.upper() == code]
        marca = info["d_marca"].iloc[0] if not info.empty else "SIN MARCA"
        color = info["color"].iloc[0] if not info.empty else "SIN COLOR"

        for tienda in tiendas_all:
            tn = _norm(tienda)
            if (tn, code) in existentes:
                continue

            stock_min = cfg_map.get("default", 4)

            exp_rows.append({
                "region": region_map.get(tn, "SIN REGION"),
                "tienda": tienda,
                "tienda_norm": tn,
                "c_barra": code,
                "d_marca": marca,
                "color": color,
                "ventas_periodo": 0,
                "stock_actual": 0,
                "stock_bodega": stock_real,
                "stock_bodega_restante": stock_real,
                "stock_minimo_dinamico": stock_min,
                "cantidad_asignada_real": 0,
                "cantidad_a_despachar": stock_min,
                "observacion": "EXPANSION"
            })

    if exp_rows:
        df = pd.concat([df, pd.DataFrame(exp_rows)], ignore_index=True)

    # =========================
    # MOTOR EXPANSIÓN
    # =========================
    mask_exp = df["observacion"] == "EXPANSION"

    for c_barra, grupo in df[mask_exp].groupby("c_barra"):
        stock = grupo["stock_bodega"].iloc[0]

        for idx, row in grupo.iterrows():
            if stock <= 0:
                break

            demanda = row["cantidad_a_despachar"]
            asignado = min(demanda, stock)

            df.loc[idx, "cantidad_asignada_real"] = asignado
            stock -= asignado

        df.loc[grupo.index, "stock_bodega_restante"] = stock


    # =========================
    # NUEVOS CÓDIGOS (FILAS)
    # =========================
    if nuevos_codigos:
        nuevos_rows = []

        for c in nuevos_codigos:
            code = str(c.get("c_barra")).upper()
            marca = c.get("d_marca", "SIN MARCA")
            color = c.get("color", "SIN COLOR")

            stock_real = stock_bodega_map.get(code, 0)

            for tienda in tiendas_all:
                tn = _norm(tienda)

                stock_min = calcular_stock_min({
                    "c_barra": code,
                    "d_marca": marca,
                    "tienda_norm": tn
                })

                nuevos_rows.append({
                    "region": region_map.get(tn, "SIN REGION"),
                    "tienda": tienda,
                    "tienda_norm": tn,
                    "c_barra": code,
                    "d_marca": marca,
                    "color": color,
                    "ventas_periodo": 0,
                    "stock_actual": 0,
                    "stock_bodega": stock_real,
                    "stock_bodega_restante": stock_real,
                    "stock_minimo_dinamico": stock_min,
                    "cantidad_asignada_real": 0,
                    "cantidad_a_despachar": stock_min,
                    "observacion": "NUEVO"
                })

        if nuevos_rows:
            df = pd.concat([df, pd.DataFrame(nuevos_rows)], ignore_index=True)

    # =========================
    # MOTOR ASIGNACIÓN EXPANSION + NUEVO
    # =========================
    mask_especial = df["observacion"].isin(["EXPANSION", "NUEVO"])

    for c_barra, grupo in df[mask_especial].groupby("c_barra"):
        stock = grupo["stock_bodega"].iloc[0]

        for idx, row in grupo.iterrows():
            demanda = row["cantidad_a_despachar"]
            if demanda <= 0:
                continue

            # EXPANSION → solo si hay stock
            if row["observacion"] == "EXPANSION":
                if stock <= 0:
                    break
                asignado = min(demanda, stock)
                stock -= asignado

            # NUEVO → si hay stock lo consume, si no, fuerza asignación
            else:  # NUEVO
                if stock > 0:
                    asignado = min(demanda, stock)
                    stock -= asignado
                else:
                    asignado = demanda  # stock mínimo teórico

            df.loc[idx, "cantidad_asignada_real"] = asignado

        df.loc[grupo.index, "stock_bodega_restante"] = max(stock, 0)

    # =========================
    # SALIDA FINAL
    # =========================
    df = df[df["observacion"] != "OK"]

    columnas = [
        "region", "tienda", "c_barra", "d_marca", "color",
        "ventas_periodo", "stock_actual",
        "stock_bodega", "stock_bodega_restante",
        "stock_minimo_dinamico",
        "cantidad_asignada_real",
        "cantidad_a_despachar",
        "observacion"
    ]

    result = df[columnas].sort_values(
        by=["region", "tienda", "d_marca", "c_barra"]
    )

    return result