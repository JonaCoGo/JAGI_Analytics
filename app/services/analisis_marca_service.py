# analisis_marca_service.py

import os
import sqlite3
import pandas as pd

from app.repositories.analisis_marca_repository import (
    get_top10_marca,
    get_productos_marca_sin_ventas,
    get_tiendas_configuradas,
    get_stock_por_barra,
)

from app.database import DATA_DIR
from app.utils.text import _norm

def get_analisis_marca(marca: str) -> dict:
    """
    Lógica de negocio para el análisis completo de una marca.
    Devuelve la estructura exacta que espera el frontend.
    """

    db_path = os.path.join(DATA_DIR, "jagi_mahalo.db")
    conn = sqlite3.connect(db_path)

    try:
        marca_norm = marca.upper().strip()

        # 1. TOP 10 productos
        df_top10 = get_top10_marca(conn, marca_norm)

        if df_top10.empty:
            df_top10 = get_productos_marca_sin_ventas(conn, marca_norm)

        # 2. Tiendas configuradas
        df_tiendas = get_tiendas_configuradas(conn)

        tiendas_dict = df_tiendas.set_index("raw_name")["clean_name"].to_dict()
        regiones_dict = df_tiendas.set_index("clean_name")["region"].to_dict()

        top10_detalles = []
        tiendas_con_top10 = set()

        # 3. Detalle por producto
        for _, fila in df_top10.iterrows():
            barra = str(fila["c_barra"])

            df_stock = get_stock_por_barra(conn, barra)

            tiendas_con_producto = [
                tiendas_dict[r]
                for r in df_stock[df_stock["saldo_disponible"] > 0]["d_almacen"]
                if r in tiendas_dict
            ]

            tiendas_con_top10.update(tiendas_con_producto)

            tiendas_sin_producto = [
                t for t in tiendas_dict.values() if t not in tiendas_con_producto
            ]

            top10_detalles.append({
                "c_barra": barra,
                "color": str(fila["color"]) if pd.notna(fila["color"]) else "N/A",
                "ventas_30d": int(fila["ventas_30d"]),
                "tiendas_con_producto": tiendas_con_producto,
                "tiendas_sin_producto": tiendas_sin_producto,
                "stock_total": int(df_stock["saldo_disponible"].sum()),
                "potencial_faltante": len(tiendas_sin_producto),
            })

        # 4. Análisis por tienda
        analisis_tiendas = []
        for tienda in tiendas_dict.values():
            productos_con = [p for p in top10_detalles if tienda in p["tiendas_con_producto"]]
            productos_sin = [p for p in top10_detalles if tienda not in p["tiendas_con_producto"]]

            analisis_tiendas.append({
                "tienda": tienda,
                "region": regiones_dict.get(tienda, "N/A"),
                "productos_top10": len(productos_con),
                "productos_faltantes": len(productos_sin),
                "ventas_top10": sum(p["ventas_30d"] for p in productos_con),
                "stock_top10": 0,
            })

        # 5. Respuesta final
        return {
            "marca": marca,
            "resumen": {
                "total_productos": len(top10_detalles),
                "tiendas_totales": len(tiendas_dict),
                "tiendas_con_top10": len(tiendas_con_top10),
                "oportunidades_redistribucion": sum(
                    p["potencial_faltante"] for p in top10_detalles
                ),
            },
            "top10": top10_detalles,
            "tiendas": analisis_tiendas,
            "recomendaciones": [
                f"Se detectaron {len(tiendas_con_top10)} tiendas con el top 10."
            ],
        }

    finally:
        conn.close()