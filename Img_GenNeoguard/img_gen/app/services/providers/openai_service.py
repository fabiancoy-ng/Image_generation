"""
Servicio para la API de OpenAI.

FASE 1 - generate() (punto de entrada):
  - Usa resolve_model_type() para saber si el modelo es TEXT o IMAGE.
  - Enruta a _generate_text() o _generate_image() según corresponda.
  - Ambos devuelven GenerationResponse con content o image_base64.

FASE 2 - _generate_text():
  - Soporta ventana de contexto: conversation_id opcional.
  - use_summary_context: True=resumir historial, False=historial completo.
  - Llama a POST /v1/chat/completions con messages (historial + prompt).
"""
import base64
import requests
from app.schemas.generation import (
    GenerationResponse,
    ModelType,
    IMAGE_EDIT_MODELS,
)
from app.core.config import settings
from app.services.context_store import get_history, append_messages
from .base import BaseProviderService


def _build_openai_messages(history: list[dict], current_prompt: str) -> list[dict]:
    """Convierte historial + prompt actual al formato messages de OpenAI."""
    messages = []
    for m in history:
        role = "assistant" if m["role"] == "assistant" else "user"
        messages.append({"role": role, "content": m["content"]})
    messages.append({"role": "user", "content": current_prompt})
    return messages


async def _summarize_openai(history: list[dict], model: str, headers: dict) -> str:
    """Resume la conversación usando el mismo modelo. Una sola llamada."""
    text_parts = [f"{m['role']}: {m['content']}" for m in history]
    prompt = "Resume brevemente esta conversación preservando hechos clave y contexto. Resumen:\n\n" + "\n".join(text_parts)
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 500,
    }
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=data,
    )
    if resp.status_code != 200:
        raise ValueError(f"Error al resumir: {resp.text}")
    return resp.json()["choices"][0]["message"]["content"].strip()




class OpenAIProviderService(BaseProviderService):
    """Implementación para OpenAI: Chat Completions, Images Generations, Images Edits."""

    async def generate(self, request) -> GenerationResponse:
        """
        Punto de entrada principal para OpenAI.
        Salida esperada: Un objeto GenerationResponse con texto o imagen en Base64.
        """
        model_type = self.resolve_model_type(request)
        api_key = settings.OPENAI_API_KEY

        if not api_key:
            raise ValueError("La API Key de OpenAI no está configurada")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        # Enrutar según tipo: texto -> Chat Completions, imagen -> Images Generations
        if model_type == ModelType.TEXT:
            return await self._generate_text(request, headers)
        elif model_type == ModelType.IMAGE:
            return await self._generate_image(request, headers)
        else:
            raise ValueError(f"Tipo de modelo '{model_type}' no soportado para OpenAI")

    async def _generate_text(self, request, headers: dict) -> GenerationResponse:
        """
        Chat Completions con soporte de ventana de contexto.
        - conversation_id: mantiene historial por ID.
        - use_summary_context: True=resumir, False=historial completo.
        """
        conversation_id = getattr(request, "conversation_id", None)
        use_summary = getattr(request, "use_summary_context", False)

        history = get_history(conversation_id) if conversation_id else []
        if use_summary and history:
            summary = await _summarize_openai(history, request.model.value, headers)
            messages = [
                {"role": "system", "content": f"Resumen de la conversación:\n{summary}"},
                {"role": "user", "content": request.prompt},
            ]
        elif history:
            messages = _build_openai_messages(history, request.prompt)
        else:
            messages = [{"role": "user", "content": request.prompt}]

        data = {
            "model": request.model.value,
            "messages": messages,
            "temperature": 1,
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
        )
        if response.status_code != 200:
            raise ValueError(f"Error de OpenAI: {response.text}")

        content = response.json()["choices"][0]["message"]["content"]

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

    async def _generate_image(self, request, headers: dict) -> GenerationResponse:
        """
        Llama al endpoint gpt image de OpenAI.
        
        Funciona para: Generar imágenes a partir de una descripción textual.
        Requiere: Formato de respuesta b64_json para recibir la imagen directamente.
        Salida esperada: String en formato Base64 de la imagen generada.
        """
        # GPT image models devuelven b64_json por defecto; dall-e requeriría response_format
        data = {
            "model": request.model.value,
            "prompt": request.prompt,
            "quality": "high",
            "n": 1,
            "size": "1024x1024",
        }

        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json=data,
        )
        if response.status_code != 200:
            raise ValueError(f"Error de imagen de OpenAI: {response.text}")

        result = response.json()
        try:
            image_base64 = result["data"][0]["b64_json"]
        except (KeyError, IndexError) as exc:
            raise ValueError(f"Fallo al procesar la respuesta de imagen: {exc}")

        return GenerationResponse(
            image_base64=image_base64,
            model_used=request.model.value,
            provider=request.provider.value,
        )

    async def edit_image(
        self,
        prompt: str,
        model: str,
        image_data_urls: list[str],
    ) -> GenerationResponse:
        """
        Edita imágenes usando POST /v1/images/edits.
        Recibe imágenes como data URLs (data:image/...;base64,...) ya validadas por el endpoint.
        """
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("La API Key de OpenAI no está configurada")

        if not image_data_urls:
            raise ValueError("Se requiere al menos una imagen de entrada")

        if model not in IMAGE_EDIT_MODELS:
            raise ValueError(
                f"Modelo '{model}' no soportado para edición. "
                f"Usa uno de: {', '.join(IMAGE_EDIT_MODELS)}"
            )

        payload = {
            "model": model,
            "prompt": prompt,
            "images": [{"image_url": url} for url in image_data_urls],
            "n": 1,
            "size": "1024x1024",
            "quality": "high",
        }

        response = requests.post(
            "https://api.openai.com/v1/images/edits",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json=payload,
        )

        if response.status_code != 200:
            raise ValueError(f"Error de edición de OpenAI: {response.text}")

        result = response.json()
        try:
            image_base64 = result["data"][0]["b64_json"]
        except (KeyError, IndexError) as exc:
            raise ValueError(f"Fallo al procesar la respuesta: {exc}")

        return GenerationResponse(
            image_base64=image_base64,
            model_used=model,
            provider="OpenAI",
        )

