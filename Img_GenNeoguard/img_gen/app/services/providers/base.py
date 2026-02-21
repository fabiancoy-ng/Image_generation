"""
Clase base abstracta para todos los proveedores.

FASE 1 - Contrato común:
  - Todos los proveedores deben implementar generate(request) -> GenerationResponse.
  - El request es un objeto con .prompt, .model, .provider (SimpleNamespace desde el endpoint).

FASE 2 - resolve_model_type:
  - Usa ALL_MODELS (derivado de _MODEL_CONFIG) para saber si el modelo es TEXT o IMAGE.
  - TEXT -> Chat Completions (o equivalente en Gemini)
  - IMAGE -> Images Generations (o equivalente)
  - Es estático porque no depende del estado de la instancia.

FASE 3 - Por qué abstracto:
  - Obliga a cada proveedor a implementar generate(). No se puede instanciar BaseProviderService.
  - Facilita que ServiceFactory devuelva "cualquier servicio" que cumpla el contrato.
"""
from abc import ABC, abstractmethod
from app.schemas.generation import GenerationResponse, ModelType, ALL_MODELS


class BaseProviderService(ABC):
    """Interfaz que deben cumplir OpenAI, Gemini y cualquier proveedor futuro."""

    @abstractmethod
    async def generate(self, request) -> GenerationResponse:
        """Genera contenido (texto o imagen) según el modelo solicitado."""
        pass

    @staticmethod
    def resolve_model_type(request) -> ModelType:
        """
        Busca en ALL_MODELS si el modelo es TEXT o IMAGE.
        Los servicios usan esto para decidir qué endpoint externo llamar.
        """
        model_type = ALL_MODELS.get(request.model)
        if model_type is None:
            raise ValueError(f"El modelo '{request.model}' no tiene un tipo registrado")
        return model_type

