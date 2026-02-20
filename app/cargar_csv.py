import pandas as pd
import os
import logging
from sqlalchemy import text
from app.database import engine, DATA_DIR

logger = logging.getLogger(__name__)


def resetear_y_cargar():
    inputs_dir = os.path.join(DATA_DIR, "inputs")

    archivos = {
        "ventas_saldos_raw":    os.path.join(inputs_dir, "1.Ventas-Saldos.csv"),
        "inventario_bodega_raw": os.path.join(inputs_dir, "2.Inventario-Bodega.csv"),
        "ventas_historico_raw": os.path.join(inputs_dir, "3.Ventas-Historico.csv"),
    }

    tablas_raw = list(archivos.keys())

    with engine.begin() as conn:  # begin() = auto-commit al salir sin error
        # Paso 1: eliminar tablas _raw
        for tabla in tablas_raw:
            logger.info(f"Eliminando tabla {tabla} si existe...")
            conn.execute(text(f"DROP TABLE IF EXISTS {tabla}"))
        logger.info("Tablas RAW eliminadas.")

    # Paso 2: cargar cada CSV y recrear la tabla
    for tabla, archivo_path in archivos.items():
        if not os.path.exists(archivo_path):
            logger.error(f"Archivo no encontrado: {archivo_path}")
            raise FileNotFoundError(f"No se encontro el archivo: {archivo_path}")

        logger.info(f"Cargando {os.path.basename(archivo_path)} -> {tabla} ...")

        df = pd.read_csv(archivo_path, encoding="latin1", sep=";")

        # Limpiar columnas "Unnamed"
        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

        # Normalizar nombres de columnas
        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace(r"[^a-z0-9_]", "", regex=True)
        )

        # Guardar en BD via SQLAlchemy (usa el engine compartido)
        df.to_sql(tabla, engine, if_exists="replace", index=False)
        logger.info(f"{len(df)} filas insertadas en {tabla}")

    logger.info(f"Tablas RAW recreadas exitosamente.")


if __name__ == "__main__":
    resetear_y_cargar()