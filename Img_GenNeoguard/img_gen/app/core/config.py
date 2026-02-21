"""
Configuración central de la aplicación.

FASE 1 - Carga de variables:
  - pydantic-settings lee automáticamente desde .env en la raíz del proyecto.
  - No hace falta usar python-dotenv manualmente; BaseSettings lo gestiona.

FASE 2 - Valores por defecto:
  - API_V1_STR y PROJECT_NAME tienen valores por defecto si no se definen en .env.
  - Las API Keys son Optional para que la app arranque sin ellas; los servicios
    validan en tiempo de ejecución y lanzan error claro si faltan.

FASE 3 - Uso:
  - Se importa 'settings' y se accede a settings.OPENAI_API_KEY, etc.
  - case_sensitive=True evita que "openai_api_key" sobrescriba "OPENAI_API_KEY".
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuración tipada accesible desde toda la aplicación."""
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Image Generation API"

    # API Keys: se leen desde .env; si faltan, los servicios lanzan ValueError
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    class Config:
        case_sensitive = True
        env_file = ".env"


# Instancia global: un solo punto de acceso a la configuración
settings = Settings()

