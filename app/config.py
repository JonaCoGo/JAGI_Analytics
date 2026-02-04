# app/config.py

import os
import sys
from pathlib import Path
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from dotenv import load_dotenv

# Detectar directorio raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Intentar cargar .env
env_path = BASE_DIR / ".env"
env_loaded = load_dotenv(env_path)


class DatabaseConfig(BaseModel):
    """
    Configuración de base de datos con validación estricta.
    
    Ejemplos:
        # SQLite (desarrollo)
        DB_TYPE=sqlite
        DB_PATH=data/jagi_mahalo.db
        
        # PostgreSQL (producción)
        DB_TYPE=postgresql
        DB_HOST=localhost
        DB_PORT=5432
        DB_NAME=jagi_mahalo
        DB_USER=admin
        DB_PASSWORD=contraseña_segura_aqui
    """
    
    type: Literal["sqlite", "postgresql"] = Field(
        description="Tipo de base de datos"
    )
    
    # SQLite
    path: Optional[str] = Field(
        default="data/jagi_mahalo.db",
        description="Ruta del archivo SQLite (solo para type=sqlite)"
    )
    
    # PostgreSQL
    host: Optional[str] = Field(
        default=None,
        description="Host de PostgreSQL (requerido si type=postgresql)"
    )
    port: Optional[int] = Field(
        default=None,
        description="Puerto de PostgreSQL (requerido si type=postgresql)"
    )
    name: Optional[str] = Field(
        default=None,
        description="Nombre de la base de datos (requerido si type=postgresql)"
    )
    user: Optional[str] = Field(
        default=None,
        description="Usuario de PostgreSQL (requerido si type=postgresql)"
    )
    password: Optional[str] = Field(
        default=None,
        description="Contraseña de PostgreSQL (requerido si type=postgresql)"
    )
    
    @field_validator("type")
    @classmethod
    def validate_db_type(cls, v: str) -> str:
        """Valida que el tipo de BD sea válido."""
        if v not in ["sqlite", "postgresql"]:
            raise ValueError(
                f"DB_TYPE inválido: '{v}'\n"
                f"Valores permitidos: sqlite, postgresql"
            )
        return v
    
    @model_validator(mode='after')
    def validate_postgresql_config(self):
        """Valida que si usas PostgreSQL, todos los campos estén presentes."""
        if self.type == "postgresql":
            missing_fields = []
            
            if not self.host:
                missing_fields.append("DB_HOST")
            if not self.port:
                missing_fields.append("DB_PORT")
            if not self.name:
                missing_fields.append("DB_NAME")
            if not self.user:
                missing_fields.append("DB_USER")
            if not self.password:
                missing_fields.append("DB_PASSWORD")
            
            if missing_fields:
                raise ValueError(
                    f"\n{'='*60}\n"
                    f"❌ CONFIGURACIÓN INCOMPLETA PARA POSTGRESQL\n"
                    f"{'='*60}\n"
                    f"Faltan estas variables en tu archivo .env:\n"
                    f"{chr(10).join(f'  - {field}' for field in missing_fields)}\n\n"
                    f"💡 SOLUCIÓN:\n"
                    f"Edita tu archivo .env y agrega:\n"
                    f"{chr(10).join(f'{field}=tu_valor_aqui' for field in missing_fields)}\n"
                    f"{'='*60}\n"
                )
            
            # Validar password insegura
            if self.password in ["postgres", "password", "admin", "123456"]:
                raise ValueError(
                    f"\n{'='*60}\n"
                    f"🚨 CONTRASEÑA INSEGURA DETECTADA\n"
                    f"{'='*60}\n"
                    f"No uses contraseñas comunes en producción.\n\n"
                    f"Contraseñas prohibidas:\n"
                    f"  - postgres\n"
                    f"  - password\n"
                    f"  - admin\n"
                    f"  - 123456\n\n"
                    f"💡 Genera una segura en:\n"
                    f"https://passwordsgenerator.net/\n"
                    f"{'='*60}\n"
                )
        
        return self
    
    def get_database_url(self) -> str:
        """Construye la URL de conexión según el tipo de BD."""
        if self.type == "sqlite":
            return f"sqlite:///{self.path}"
        else:
            return (
                f"postgresql://{self.user}:{self.password}"
                f"@{self.host}:{self.port}/{self.name}"
            )


class AppConfig(BaseModel):
    """Configuración general de la aplicación."""
    
    debug: bool = Field(
        default=False,
        description="Modo debug (NUNCA True en producción)"
    )
    
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Nivel de logging"
    )
    
    environment: Literal["development", "testing", "staging", "production"] = Field(
        default="development",
        description="Entorno de ejecución actual"
    )
    
    @model_validator(mode='after')
    def validate_production_safety(self):
        """Previene configuraciones peligrosas en producción."""
        if self.environment == "production":
            if self.debug:
                raise ValueError(
                    f"\n{'='*60}\n"
                    f"🚨 CONFIGURACIÓN PELIGROSA\n"
                    f"{'='*60}\n"
                    f"No puedes tener DEBUG=True en producción.\n\n"
                    f"Esto expone:\n"
                    f"  - Stack traces completos a usuarios\n"
                    f"  - Rutas de archivos del servidor\n"
                    f"  - Queries SQL ejecutadas\n"
                    f"  - Variables de entorno\n\n"
                    f"💡 SOLUCIÓN:\n"
                    f"En tu .env, cambia a:\n"
                    f"DEBUG=False\n"
                    f"{'='*60}\n"
                )
        
        return self


class Settings(BaseModel):
    """
    Configuración global del sistema JAGI ERP.
    
    Esta clase centraliza TODA la configuración y la valida
    antes de que la aplicación inicie.
    """
    
    app: AppConfig
    database: DatabaseConfig
    
    class Config:
        """Configuración de Pydantic."""
        case_sensitive = False
        extra = "ignore"


def load_settings() -> Settings:
    """
    Carga y valida la configuración completa del sistema.
    
    Esta función se ejecuta UNA SOLA VEZ al iniciar la aplicación.
    Si hay algún error, la aplicación NO inicia.
    
    Returns:
        Settings: Configuración validada
        
    Raises:
        SystemExit: Si la configuración es inválida o falta .env
    """
    
    # Verificar que exista .env
    if not env_loaded and not env_path.exists():
        print("\n" + "="*60)
        print("❌ ERROR: Archivo .env no encontrado")
        print("="*60)
        print(f"\nBuscado en: {env_path}")
        print("\n💡 SOLUCIÓN:")
        print("1. Copia el archivo de ejemplo:")
        print(f"   cp .env.example .env")
        print("\n2. Edita .env y completa tus valores")
        print("\n3. Reinicia la aplicación")
        print("\n📖 Documentación completa:")
        print("   https://github.com/JonaCoGo/jagi_erp#configuracion")
        print("="*60 + "\n")
        sys.exit(1)
    
    try:
        # Leer variables de entorno
        settings = Settings(
            app=AppConfig(
                debug=os.getenv("DEBUG", "False").lower() in ("true", "1", "yes"),
                log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
                environment=os.getenv("ENVIRONMENT", "development").lower(),
            ),
            database=DatabaseConfig(
                type=os.getenv("DB_TYPE", "").lower() or "sqlite",
                path=os.getenv("DB_PATH", "data/jagi_mahalo.db"),
                host=os.getenv("DB_HOST"),
                port=int(os.getenv("DB_PORT", "0")) if os.getenv("DB_PORT") else None,
                name=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
            )
        )
        
        return settings
        
    except ValueError as e:
        print("\n" + "="*60)
        print("❌ ERROR DE CONFIGURACIÓN")
        print("="*60)
        print(str(e))
        print("\n📝 Verifica tu archivo .env:")
        print(f"   {env_path}")
        print("\n📖 Consulta el archivo .env.example para ver ejemplos")
        print("="*60 + "\n")
        sys.exit(1)


# Singleton: Se carga UNA SOLA VEZ al importar
settings = load_settings()