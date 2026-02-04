# app/database.py

"""
Capa de abstracción para conexiones a base de datos.
Soporta SQLite (desarrollo) y PostgreSQL (producción).

Actualizado: Ahora usa sistema de logging profesional.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
import logging
import os

# Importar configuración validada
from app.config import settings

# Obtener logger para este módulo
logger = logging.getLogger(__name__)

# ==========================================
# CONFIGURACIÓN DE BASE DE DATOS
# ==========================================

DATABASE_URL = settings.database.get_database_url()
DB_TYPE = settings.database.type

# ==========================================
# CREAR ENGINE SEGÚN TIPO DE BD
# ==========================================

if DB_TYPE == "postgresql":
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=settings.app.debug,
    )
    logger.info(
        f"🐘 Conectado a PostgreSQL | "
        f"Host: {settings.database.host}:{settings.database.port} | "
        f"Database: {settings.database.name}"
    )

else:  # SQLite
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    os.makedirs(DATA_DIR, exist_ok=True)
    DB_PATH = os.path.join(DATA_DIR, settings.database.path.split('/')[-1])
    
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.app.debug,
    )
    logger.info(f"📦 Conectado a SQLite: {DB_PATH}")

# Exportar para uso en otros módulos
DB_NAME = settings.database.name or "jagi_mahalo.db"
DATA_DIR = DATA_DIR if DB_TYPE == "sqlite" else None
DB_PATH = DB_PATH if DB_TYPE == "sqlite" else None

# ==========================================
# SESIONES Y BASE DECLARATIVA
# ==========================================

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def get_db():
    """Generador de sesiones para FastAPI dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_connection():
    """Obtiene una conexión raw para pandas.read_sql()."""
    return engine.connect()


def test_connection():
    """Prueba la conexión a la base de datos."""
    try:
        with engine.connect() as conn:
            if DB_TYPE == "postgresql":
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                logger.info(f"✅ PostgreSQL conectado | Versión: {version}")
            else:
                result = conn.execute(text("SELECT sqlite_version()"))
                version = result.fetchone()[0]
                logger.info(f"✅ SQLite conectado | Versión: {version}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error de conexión a base de datos: {str(e)}", exc_info=True)
        return False


def get_db_info():
    """Retorna información sobre la base de datos actual."""
    masked_url = DATABASE_URL
    if settings.database.password:
        masked_url = DATABASE_URL.replace(settings.database.password, "***")
    
    info = {
        "type": DB_TYPE,
        "url": masked_url,
        "environment": settings.app.environment,
    }
    
    logger.debug(f"DB Info: {info}")
    return info

# ==========================================
# HELPERS PARA QUERIES COMPATIBLES
# ==========================================

def date_subtract_days(days: int) -> str:
    """Genera SQL compatible para restar días de la fecha actual."""
    if DB_TYPE == "postgresql":
        return f"CURRENT_DATE - INTERVAL '{days} days'"
    else:
        return f"DATE('now', '-{days} days')"


def date_format_convert(column: str, sqlite_format: str = "DD/MM/YYYY") -> str:
    """Convierte formato de fecha según el tipo de BD."""
    if DB_TYPE == "postgresql":
        pg_format = sqlite_format.replace("YYYY", "YYYY").replace("MM", "MM").replace("DD", "DD")
        return f"TO_DATE({column}, '{pg_format}')"
    else:
        if sqlite_format == "DD/MM/YYYY":
            return f"DATE(substr({column},7,4)||'-'||substr({column},4,2)||'-'||substr({column},1,2))"
        else:
            return f"DATE({column})"


def current_date() -> str:
    """Retorna SQL para fecha actual según BD."""
    if DB_TYPE == "postgresql":
        return "CURRENT_DATE"
    else:
        return "DATE('now')"

# ==========================================
# INICIALIZACIÓN
# ==========================================

if __name__ != "__main__":
    test_connection()