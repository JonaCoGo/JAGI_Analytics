# 🏢 JAGI Analytics for Mahalo

Python · FastAPI · Analytics Platform

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Plataforma de análisis operativo y soporte a la toma de decisiones,
> diseñada para trabajar sobre datos exportados desde el ERP Mahalo
> (WebSaaS), enfocada en inventarios, ventas y abastecimiento en
> entornos retail.

## 🎯 Descripción General

JAGI Analytics for Mahalo es una herramienta analítica que procesa
información histórica y actual proveniente de archivos CSV exportados
desde el ERP Mahalo (WebSaaS).

El sistema no ejecuta movimientos operativos ni reemplaza al ERP
principal.\
Su función es **analizar, consolidar y presentar información** para
facilitar decisiones informadas que posteriormente se ejecutan
directamente en Mahalo.

## 📋 Características

-   ✅ Carga automática de datos desde archivos CSV exportados desde
    Mahalo
-   📊 Dashboard interactivo con métricas clave
-   📦 Análisis de inventario por tienda, región y referencia
-   🔄 Sugerencias analíticas de reabastecimiento basadas en ventas
    históricas
-   🏷️ Análisis por marca (Top 10, cobertura, faltantes)
-   📈 Generación de reportes Excel automatizados
-   🔍 Consulta histórica de productos (datos importados)

## 🚫 Alcance y Limitaciones

Este sistema: - ❌ No crea ni modifica inventarios reales - ❌ No
ejecuta movimientos logísticos - ❌ No reemplaza el ERP Mahalo - ✅
Apoya decisiones operativas y estratégicas - ✅ Funciona como capa
analítica especializada

## 🔄 Flujo de Datos

1.  Exportación de información desde Mahalo (CSV, periodo anual
    completo).
2.  Carga de archivos en JAGI Analytics.
3.  Eliminación y recarga total de datos (modelo analítico actual).
4.  Procesamiento y análisis de inventarios y ventas.
5.  Generación de reportes y sugerencias.
6.  Ejecución manual de decisiones en Mahalo.

## 🚀 Instalación

### Prerrequisitos

-   Python 3.12+
-   pip (gestor de paquetes de Python)

### 1️⃣ Clonar el repositorio

``` bash
git clone https://github.com/JonaCoGo/JAGI_Analytics.git
cd JAGI_Analytics
```

### 2️⃣ Crear entorno virtual

``` bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
# source venv/bin/activate
```

### 3️⃣ Instalar dependencias

``` bash
pip install -r requirements.txt
```

### 4️⃣ Crear base de datos

``` bash
python scripts/create_schema.py
python scripts/seed_data.py
```

### 5️⃣ Configurar Variables de Entorno

Copiar archivo de ejemplo:

``` bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Editar `.env`:

``` env
DB_TYPE=sqlite
DB_PATH=data/jagi_mahalo.db
```

### 6️⃣ Ejecutar servidor

Opción manual:

``` bash
uvicorn app.main:app --reload
```

Opción rápida en Windows: - Ejecutar `Start.bat` desde la raíz
`C:\JAGI_Analytics` - El sistema iniciará el servidor y abrirá
automáticamente el `index.html`

## 🏗️ Arquitectura

    JAGI_Analytics/
    ├── app/
    │   ├── main.py              # API FastAPI
    │   ├── services/            # Lógica analítica
    │   ├── repositories/        # Acceso a datos
    │   └── reports/             # Generación de reportes
    ├── static/                  # Frontend (HTML/CSS/JS)
    ├── scripts/                 # Utilidades BD
    └── test/                    # Pruebas automatizadas

## 🧪 Testing

``` bash
pytest
```

Cobertura actual aproximada: \~40% (en mejora continua)

## 🛠️ Stack Tecnológico

  Componente      Tecnología
  --------------- ----------------------------------
  Backend         FastAPI + Python 3.12+
  Base de datos   SQLite (desarrollo)
  Frontend        HTML5 + TailwindCSS + Vanilla JS
  Testing         Pytest
  Reportes        Pandas + OpenPyXL

## 📖 Documentación API

Swagger UI: http://127.0.0.1:8000/docs\
ReDoc: http://127.0.0.1:8000/redoc

## 🔐 Seguridad

-   El archivo `.env` nunca se sube a Git
-   Usar contraseñas seguras (16+ caracteres)
-   En producción, usar variables de entorno del servidor

## 🤝 Contribuciones

Ver `CONTRIBUTING.md` para convenciones de commits y flujo de trabajo.

## 📝 Licencia

Proyecto de uso educativo y profesional bajo licencia MIT.

## 👨‍💻 Autor

**Jonatan Corrales Gómez**\
Técnico en Programación de Aplicaciones y Servicios para la Nube - SENA

GitHub: https://github.com/JonaCoGo\
LinkedIn: https://www.linkedin.com/in/jonatancorralesgomez

## 📌 Estado del Proyecto

En desarrollo activo.\
Enfocado en analítica, calidad de datos y soporte a decisiones
operativas.
