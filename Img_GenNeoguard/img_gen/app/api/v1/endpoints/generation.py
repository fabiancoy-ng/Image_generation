"""
Endpoints de generación y edición de contenido.

FASE 1 - Endpoints dinámicos por proveedor:
  - _create_provider_endpoint() genera una función por cada Provider (OpenAI, Gemini).
  - Cada endpoint recibe prompt + model vía Form, valida con BaseGenerationRequest,
    y delega en ServiceFactory.get_service() -> service.generate().
  - Se usa SimpleNamespace para empaquetar prompt, model, provider en un objeto
    que los servicios esperan (acceso vía .prompt, .model, etc.).

FASE 2 - Endpoints informativos:
  - GET /models: lista modelos por proveedor para que el frontend llene los dropdowns.
  - GET /edit-info: formatos permitidos y modelos de edición para la UI.

FASE 3 - Edición de imágenes:
  - POST /openai/edit recibe multipart: prompt, model, y múltiples archivos.
  - Valida extensiones y MIME types antes de convertir a base64 data URLs.
  - Convierte cada archivo a data:image/...;base64,... porque la API de OpenAI
    acepta image_url en ese formato (no multipart directo para edits).
"""
import base64
from types import SimpleNamespace
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Form, File, UploadFile
from pydantic import ValidationError

from app.schemas.generation import (
    Provider,
    GenerationResponse,
    ProviderModels,
    ModelInfo,
    BaseGenerationRequest,
    ALL_MODELS,
    PROVIDER_MODELS,
    PROVIDER_MODEL_ENUMS,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_IMAGE_MIMETYPES,
    IMAGE_EDIT_MODELS,
)
from app.services.factory import ServiceFactory

router = APIRouter()

# Mensaje informativo sobre formatos permitidos (para documentación y errores)
ALLOWED_FORMATS_MSG = "Formatos permitidos: PNG, JPEG, GIF, WEBP (.png, .jpg, .jpeg, .gif, .webp)"


def _create_provider_endpoint(provider: Provider):
    """
    Factory de endpoints: crea una función async por proveedor.
    Se usa model_enum como tipo del parámetro 'model' para que Swagger muestre
    solo los modelos de ese proveedor en un dropdown (no todos mezclados).
    """
    model_enum = PROVIDER_MODEL_ENUMS[provider]

    async def generate(
        prompt: str = Form(..., description="El prompt de entrada para la generación"),
        model: model_enum = Form(..., description=f"El modelo de {provider.value} a utilizar"),
        conversation_id: Optional[str] = Form(None, description="ID de conversación para mantener contexto"),
        use_summary_context: bool = Form(False, description="True=resumir historial, False=historial completo"),
    ):
        # Validar prompt (longitud, sanitización contra inyecciones)
        try:
            validated = BaseGenerationRequest(prompt=prompt)
        except ValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        # Empaquetar en objeto que los servicios esperan
        request = SimpleNamespace(
            prompt=validated.prompt,
            model=model,
            provider=provider,
            conversation_id=conversation_id,
            use_summary_context=use_summary_context,
        )

        # Delegar en el servicio del proveedor
        try:
            service = ServiceFactory.get_service(provider)
            return await service.generate(request)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            )

    # Nombres únicos evitan colisiones en operationId de OpenAPI (Swagger)
    generate.__name__ = f"generate_{provider.value.lower()}"
    generate.__qualname__ = generate.__name__
    return generate


# ── Registro Dinámico de Rutas ──
# Itera sobre los proveedores definidos en el Enum y crea un endpoint POST /{proveedor} para cada uno.
for _provider in Provider:
    router.post(
        f"/{_provider.value.lower()}",
        response_model=GenerationResponse,
        summary=f"Generar contenido con {_provider.value}",
    )(_create_provider_endpoint(_provider))


@router.get("/models", response_model=list[ProviderModels])
def list_models():
    """
    Lista todos los modelos disponibles agrupados por su proveedor.
    
    Funciona para: Informar al cliente qué modelos existen y si son de texto o imagen.
    Salida esperada: Una lista de objetos ProviderModels con sus respectivos metadatos.
    """
    return [
        ProviderModels(
            provider=provider,
            models=[ModelInfo(id=m.value, type=ALL_MODELS[m]) for m in models],
        )
        for provider, models in PROVIDER_MODELS.items()
    ]


@router.get(
    "/edit-info",
    summary="Información para edición de imágenes",
)
def get_edit_info():
    """
    Devuelve formatos permitidos y modelos disponibles para edición de imágenes.
    Útil para mostrar en la UI qué archivos puede adjuntar el usuario.
    """
    return {
        "allowed_extensions": sorted(ALLOWED_IMAGE_EXTENSIONS),
        "allowed_formats": "PNG, JPEG, GIF, WEBP",
        "max_images": 16,
        "min_images": 1,
        "models": sorted(IMAGE_EDIT_MODELS),
    }


@router.post(
    "/openai/edit",
    response_model=GenerationResponse,
    summary="Editar imágenes con OpenAI",
)
async def edit_images_openai(
    prompt: str = Form(..., description="Descripción de la edición deseada"),
    model: str = Form(
        ...,
        description=f"Modelo de edición. Opciones: {', '.join(IMAGE_EDIT_MODELS)}",
    ),
    images: list[UploadFile] = File(
        ...,
        description=f"Imágenes a editar (1-16). {ALLOWED_FORMATS_MSG}",
    ),
):
    """
    Edita una o más imágenes según el prompt usando el endpoint /images/edits de OpenAI.
    
    **Formatos permitidos:** PNG, JPEG, GIF, WEBP (.png, .jpg, .jpeg, .gif, .webp)
    **Límite:** 1 a 16 imágenes para modelos GPT.
    """
    # Validar cantidad (OpenAI Images Edits acepta 1-16 para modelos GPT)
    if len(images) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Se requiere al menos una imagen. {ALLOWED_FORMATS_MSG}",
        )
    if len(images) > 16:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Máximo 16 imágenes. {ALLOWED_FORMATS_MSG}",
        )

    # Convertir cada archivo a data URL base64 (formato que espera la API de OpenAI)
    data_urls = []
    for img in images:
        ext = "." + img.filename.rsplit(".", 1)[-1].lower() if "." in img.filename else ""
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Archivo '{img.filename}' no permitido. {ALLOWED_FORMATS_MSG}",
            )
        content = await img.read()
        mime = img.content_type or "image/png"
        if mime not in ALLOWED_IMAGE_MIMETYPES:
            mime = "image/png"  # Fallback: cliente puede enviar Content-Type incorrecto
        b64 = base64.b64encode(content).decode("utf-8")
        data_urls.append(f"data:{mime};base64,{b64}")

    # Validar prompt igual que en generación
    try:
        validated = BaseGenerationRequest(prompt=prompt)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    service = ServiceFactory.get_service(Provider.OPENAI)
    if not hasattr(service, "edit_image"):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="El proveedor seleccionado no soporta edición de imágenes",
        )
    return await service.edit_image(
        prompt=validated.prompt,
        model=model,
        image_data_urls=data_urls,
    )

