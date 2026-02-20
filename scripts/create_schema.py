# scripts/create_BD.py

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "jagi.db")


def create_tables(cursor):
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS map_marcas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_marca TEXT NOT NULL,
        categoria TEXT NOT NULL,
        es_manual INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS map_paises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_pais TEXT NOT NULL,
        continente TEXT NOT NULL,
        es_manual INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS map_productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_producto TEXT NOT NULL,
        categoria TEXT NOT NULL,
        es_manual INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS raw_mahalo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        marca TEXT,
        producto TEXT,
        pais TEXT,
        ventas REAL
    );
    """)


def insert_config_data(cursor):
    marcas = [
        ("Royal Canin", "Pet Food", 0),
        ("Purina", "Pet Food", 0),
        ("Hill's", "Pet Food", 0)
    ]

    paises = [
        ("Colombia", "América", 0),
        ("México", "América", 0),
        ("Chile", "América", 0)
    ]

    productos = [
        ("Adult Dog", "Perros", 0),
        ("Adult Cat", "Gatos", 0)
    ]

    cursor.executemany(
        "INSERT INTO map_marcas (nombre_marca, categoria, es_manual) VALUES (?, ?, ?)",
        marcas
    )

    cursor.executemany(
        "INSERT INTO map_paises (nombre_pais, continente, es_manual) VALUES (?, ?, ?)",
        paises
    )

    cursor.executemany(
        "INSERT INTO map_productos (nombre_producto, categoria, es_manual) VALUES (?, ?, ?)",
        productos
    )


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    if os.path.exists(DB_PATH):
        print("La base de datos ya existe.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    create_tables(cursor)
    insert_config_data(cursor)

    conn.commit()
    conn.close()

    print("Base de datos creada correctamente en:", DB_PATH)


if __name__ == "__main__":
    main()