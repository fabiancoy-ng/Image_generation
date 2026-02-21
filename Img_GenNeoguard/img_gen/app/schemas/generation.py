"""
Esquemas y configuración central de modelos/proveedores.

FASE 1 - Enums base:
  - Provider: identifica el proveedor (OpenAI, Gemini). Se usa como clave en rutas y factory.
  - ModelType: distingue si un modelo genera texto o imagen. Determina qué endpoint llamar.

FASE 2 - Configuración maestra (_MODEL_CONFIG):
  - Es la ÚNICA fuente de verdad. Para agregar un modelo nuevo, solo se edita este dict.
  - Formato: Proveedor -> { "id-modelo": ModelType }
  - Todo lo demás (Enums, ALL_MODELS, PROVIDER_MODELS) se deriva automáticamente.

FASE 3 - Derivación automática:
  - PROVIDER_MODEL_ENUMS: genera OpenAIModel, GeminiModel, etc. para dropdowns en Swagger.
  - ALL_MODELS: mapea cada modelo a su tipo (TEXT/IMAGE) para que los servicios sepan
    si llamar a Chat Completions o Images API.
  - PROVIDER_MODELS: lista de modelos por proveedor para el endpoint /models.

FASE 4 - Schemas de request/response:
  - BaseGenerationRequest: valida y sanitiza el prompt (evita inyecciones básicas).
  - GenerationResponse: formato unificado de salida para todos los proveedores.

FASE 5 - Edición de imágenes:
  - Constantes para formatos permitidos y modelos de edición (OpenAI Images Edits API).
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re


class Provider(str, Enum):
    """
    Define los proveedores de LLM soportados.
    Se usa como clave principal para organizar modelos y servicios.
    """
    OPENAI = "OpenAI"
    GEMINI = "Gemini"


class ModelType(str, Enum):
    """
    Categoriza el tipo de salida que genera un modelo.
    Permite al sistema decidir si llamar a un endpoint de chat o de imagen.
    """
    TEXT = "text"
    IMAGE = "image"


# ──────────────────────────────────────────────────────────
#  CONFIGURACIÓN: Agrega modelos/proveedores AQUÍ — fuente única de verdad.
#  Formato: Proveedor → { "id-del-modelo": ModelType }
#  Todo lo demás (enums, búsquedas, endpoints) se deriva automáticamente.
# ──────────────────────────────────────────────────────────
_MODEL_CONFIG: dict[Provider, dict[str, ModelType]] = {
    Provider.OPENAI: {
        "gpt-image-1.5": ModelType.IMAGE,
        "gpt-image-1": ModelType.IMAGE,
        "gpt-5": ModelType.TEXT,
        "gpt-5.2": ModelType.TEXT,
    },
    Provider.GEMINI: {
        "gemini-2.5-flash": ModelType.TEXT,
        "imagen-4.0-generate-001": ModelType.IMAGE,
    },
}


def _to_enum_name(model_id: str) -> str:
    """
    Convierte 'gpt-image-1.5' en 'GPT_IMAGE_1_5' para que sea un nombre válido de Enum.
    Los guiones y puntos no son válidos en identificadores Python.
    """
    return model_id.upper().replace("-", "_").replace(".", "_")


# ── Generación automática desde _MODEL_CONFIG ──
# No se crean Enums a mano; se derivan del diccionario para evitar duplicación.

# Enums por proveedor: FastAPI los usa para validar y mostrar dropdowns en Swagger
PROVIDER_MODEL_ENUMS: dict[Provider, type] = {
    prov: Enum(f"{prov.value}Model", {_to_enum_name(m): m for m in models}, type=str)
    for prov, models in _MODEL_CONFIG.items()
}

# Mapeo modelo -> tipo: los servicios llaman resolve_model_type() que usa este dict
# para decidir si invocar Chat Completions (TEXT) o Images Generations (IMAGE)
ALL_MODELS: dict = {
    PROVIDER_MODEL_ENUMS[prov][_to_enum_name(mid)]: mtype
    for prov, models in _MODEL_CONFIG.items()
    for mid, mtype in models.items()
}

# Listado de modelos por proveedor para el endpoint informativo
PROVIDER_MODELS: dict[Provider, list] = {
    prov: list(enum_cls) for prov, enum_cls in PROVIDER_MODEL_ENUMS.items()
}


# ── Schemas de Petición y Respuesta ──

class BaseGenerationRequest(BaseModel):
    """
    Schema base para cualquier petición de generación.
    Funciona para: Validar la longitud del prompt y sanitizar el contenido.
    Salida esperada: Un objeto con el prompt limpio y sin caracteres maliciosos.
    """
    prompt: str = Field(..., min_length=1, max_length=2000, description="El prompt de entrada")

    @field_validator('prompt')
    @classmethod
    def sanitize_prompt(cls, v: str) -> str:
        """
        Sanitización básica: elimina espacios sobrantes y bloquea patrones de inyección.
        No sustituye un WAF, pero evita payloads obvios (XSS, etc.) en prompts.
        """
        forbidden = [r"<script>", r"javascript:", r"exec\(", r"system\("]
        for pattern in forbidden:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("El prompt contiene patrones prohibidos")
        return v.strip()


class GenerationResponse(BaseModel):
    """
    Formato unificado de respuesta de la API.
    Funciona para: Normalizar la salida de cualquier proveedor (OpenAI, Gemini).
    Atributos:
        - content: Texto generado (si es modelo de texto).
        - image_base64: Imagen en Base64 (si es modelo de imagen).
        - image_mime_type: MIME de la imagen (p. ej. image/png) para data URL y descarga.
        - model_used: Nombre del modelo que procesó la solicitud.
        - provider: Nombre del proveedor.
    """
    content: Optional[str] = Field(None, description="Contenido de texto generado")
    image_base64: Optional[str] = Field(None, description="Imagen generada en formato Base64")
    image_mime_type: Optional[str] = Field(None, description="MIME type de la imagen (image/png, image/jpeg, etc.)")
    model_used: str
    provider: str


class ModelInfo(BaseModel):
    """Información detallada de un modelo individual."""
    id: str
    type: ModelType


class ProviderModels(BaseModel):
    """Lista de modelos agrupados por proveedor para el endpoint /models."""
    provider: Provider
    models: List[ModelInfo]


# ── Edición de imágenes (OpenAI Images Edits API) ──
# Se validan extensiones y MIME types para rechazar archivos no soportados antes de
# enviarlos a la API. frozenset permite búsqueda O(1) y evita modificaciones accidentales.

ALLOWED_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp"})
ALLOWED_IMAGE_MIMETYPES = frozenset({"image/png", "image/jpeg", "image/gif", "image/webp"})
# Modelos GPT que soportan /images/edits con hasta 16 imágenes de input
IMAGE_EDIT_MODELS = frozenset({"gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini", "chatgpt-image-latest"})

