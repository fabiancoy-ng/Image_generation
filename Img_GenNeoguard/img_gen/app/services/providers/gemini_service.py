"""
Servicio para la API de Google Gemini.

FASE 1 - Texto:
  - Soporta ventana de contexto: conversation_id opcional.
  - use_summary_context: True=resumir historial, False=historial completo.
  - contents: array de Content con role user/model (documentación Gemini).

FASE 2 - Imagen:
  - Usa client.models.generate_images() con Imagen (API key, sin Vertex AI).
  - Usa los bytes tal cual; si vienen base64, se decodifican. Se detecta el formato por magic bytes.
"""
import base64
from google import genai
from google.genai import types

from app.schemas.generation import GenerationResponse, ModelType
from app.core.config import settings
from app.services.context_store import get_history, append_messages
from .base import BaseProviderService


def _build_gemini_contents(history: list[dict], current_prompt: str) -> list:
    """Convierte historial + prompt actual al formato Content de Gemini."""
    contents = []
    for m in history:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=current_prompt)]))
    return contents


def _summarize_gemini(history: list[dict], client, model: str) -> str:
    """Resume la conversación usando el mismo modelo."""
    text_parts = [f"{m['role']}: {m['content']}" for m in history]
    prompt = "Resume brevemente esta conversación preservando hechos clave y contexto. Resumen:\n\n" + "\n".join(text_parts)
    resp = client.models.generate_content(model=model, contents=prompt)
    return resp.text.strip()


def _ensure_raw_bytes(data) -> bytes:
    """Convierte a bytes si viene base64-encoded (str o bytes ASCII)."""
    if isinstance(data, str):
        return base64.b64decode(data)
    if isinstance(data, bytes):
        # Si empieza con magic bytes de imagen, son bytes crudos
        if len(data) >= 4 and (
            data[:4] == b"\x89PNG"
            or data[:3] == b"\xff\xd8\xff"
            or (len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP")
        ):
            return data
        # Si no, intentar decodificar como base64 (la API a veces devuelve base64)
        try:
            return base64.b64decode(data)
        except Exception:
            return data
    return data


class GeminiProviderService(BaseProviderService):
    """Implementación para Gemini: texto vía generate_content, imagen vía generate_images."""

    async def generate(self, request) -> GenerationResponse:
        """
        Punto de entrada principal para Gemini.
        Salida esperada: Respuesta de texto o imagen en base64.
        """
        model_type = self.resolve_model_type(request)
        api_key = settings.GEMINI_API_KEY

        if not api_key:
            raise ValueError("La API Key de Gemini no está configurada")

        client = genai.Client(api_key=api_key)

        if model_type == ModelType.TEXT:
            conversation_id = getattr(request, "conversation_id", None)
            use_summary = getattr(request, "use_summary_context", False)

            history = get_history(conversation_id) if conversation_id else []
            config = None
            if use_summary and history:
                summary = _summarize_gemini(history, client, request.model.value)
                config = types.GenerateContentConfig(
                    system_instruction=f"Resumen de la conversación previa:\n{summary}"
                )
                contents = request.prompt
            elif history:
                contents = _build_gemini_contents(history, request.prompt)
            else:
                contents = request.prompt

            response = client.models.generate_content(
                model=request.model.value,
                contents=contents,
                config=config,
            )
            content = response.text

            if conversation_id:
                append_messages(
                    conversation_id,
                    [
                        {"role": "user", "content": request.prompt},
                        {"role": "assistant", "content": content},
                    ],
                )

            return GenerationResponse(
                content=content,
                model_used=request.model.value,
                provider=request.provider.value,
            )
        elif model_type == ModelType.IMAGE:
            config = types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="1:1",
                safety_filter_level="BLOCK_LOW_AND_ABOVE",
                person_generation="ALLOW_ADULT",
            )
            response = client.models.generate_images(
                model=request.model.value,
                prompt=request.prompt,
                config=config,
            )
            if not response.generated_images:
                raise ValueError("No se generó ninguna imagen (el prompt pudo haber sido filtrado)")

            raw = response.generated_images[0].image.image_bytes
            image_bytes = _ensure_raw_bytes(raw)

            # Detectar formato por magic bytes para MIME correcto
            if image_bytes[:4] == b"\x89PNG":
                mime = "image/png"
            elif image_bytes[:3] == b"\xff\xd8\xff":
                mime = "image/jpeg"
            elif len(image_bytes) > 12 and image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
                mime = "image/webp"
            else:
                mime = "image/png"

            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            return GenerationResponse(
                image_base64=image_base64,
                image_mime_type=mime,
                model_used=request.model.value,
                provider=request.provider.value,
            )
        else:
            raise ValueError(f"Tipo de modelo '{model_type}' no soportado para Gemini")

