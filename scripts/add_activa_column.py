# scripts/add_activa_column.py

"""
Script para agregar la columna 'activa' a la tabla config_tiendas.
Ejecutar UNA SOLA VEZ para actualizar la base de datos existente.

Uso:
    python scripts/add_activa_column.py
"""

import sqlite3
import os
from pathlib import Path

# 1. Obtenemos la ruta de la carpeta donde está este script (C:\JAGI_ERP\scripts)
script_dir = Path(__file__).parent

# 2. Subimos un nivel (a JAGI_ERP) y entramos a 'data'
DB_PATH = script_dir.parent / "data" / "jagi_mahalo.db"

def add_activa_column():
    """Agrega columna 'activa' a config_tiendas si no existe."""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: No se encontró la base de datos en {DB_PATH}")
        print(f"Directorio actual de ejecución: {os.getcwd()}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(config_tiendas)")
        columnas = [row[1] for row in cursor.fetchall()]
        
        if 'activa' in columnas:
            print("ℹ️  La columna 'activa' ya existe en config_tiendas")
            return True
        
        # Agregar la columna con valor por defecto 1 (activa)
        print("📝 Agregando columna 'activa' a config_tiendas...")
        cursor.execute("""
            ALTER TABLE config_tiendas 
            ADD COLUMN activa INTEGER DEFAULT 1
        """)
        
        # Verificar que todas las tiendas existentes estén activas
        cursor.execute("""
            UPDATE config_tiendas 
            SET activa = 1 
            WHERE activa IS NULL
        """)
        
        conn.commit()
        
        # Verificar el resultado
        cursor.execute("SELECT COUNT(*) FROM config_tiendas WHERE activa = 1")
        count = cursor.fetchone()[0]
        
        print(f"✅ Columna agregada exitosamente")
        print(f"✅ {count} tiendas marcadas como activas por defecto")
        
        return True
        
    except Exception as e:
        print(f"❌ Error al agregar columna: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


def verificar_estructura():
    """Muestra la estructura actualizada de config_tiendas."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(config_tiendas)")
        columnas = cursor.fetchall()
        
        print("\n📊 Estructura actual de config_tiendas:")
        print("-" * 60)
        for col in columnas:
            col_id, nombre, tipo, not_null, default, pk = col
            print(f"  {nombre:20} {tipo:10} {'NOT NULL' if not_null else ''} {f'DEFAULT {default}' if default else ''}")
        print("-" * 60)
        
        # Mostrar datos de ejemplo
        cursor.execute("""
            SELECT clean_name, region, fija, activa 
            FROM config_tiendas 
            LIMIT 5
        """)
        datos = cursor.fetchall()
        
        print("\n📋 Datos de ejemplo:")
        print("-" * 60)
        print(f"{'Tienda':20} {'Región':15} {'Fija':6} {'Activa':6}")
        print("-" * 60)
        for row in datos:
            print(f"{row[0]:20} {row[1]:15} {row[2]:6} {row[3]:6}")
        
    finally:
        conn.close()


if __name__ == "__main__":
    print("🚀 Iniciando actualización de base de datos...")
    print("=" * 60)
    
    if add_activa_column():
        verificar_estructura()
        print("\n✅ Actualización completada con éxito")
    else:
        print("\n❌ La actualización falló")