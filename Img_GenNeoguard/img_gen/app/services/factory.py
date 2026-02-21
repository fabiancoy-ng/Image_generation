"""
Factory de servicios por proveedor.

FASE 1 - Patrón Factory:
  - Los endpoints no conocen OpenAIProviderService ni GeminiProviderService directamente.
  - Solo piden "el servicio de OpenAI" y la factory devuelve la instancia correcta.
  - Esto permite agregar nuevos proveedores sin tocar el código de los endpoints.

FASE 2 - Registro:
  - _services mapea Provider -> clase de servicio. Cada vez que se llama get_service(),
    se instancia la clase (service_class()). No se reutilizan instancias (stateless).

FASE 3 - Extensibilidad:
  - Para agregar un proveedor: añadir al Enum Provider, crear XxxProviderService,
    y registrar en _services. Los endpoints dinámicos ya incluirán la nueva ruta.
"""
from typing import Dict, Type
from app.schemas.generation import Provider
from .providers.base import BaseProviderService
from .providers.openai_service import OpenAIProviderService
from .providers.gemini_service import GeminiProviderService


class ServiceFactory:
    """Mapeo Provider -> clase de servicio. get_service() instancia y devuelve."""

    _services: Dict[Provider, Type[BaseProviderService]] = {
        Provider.OPENAI: OpenAIProviderService,
        Provider.GEMINI: GeminiProviderService,
    }

    @classmethod
    def get_service(cls, provider: Provider) -> BaseProviderService:
        """Devuelve una instancia del servicio. Lanza ValueError si el proveedor no existe."""
        service_class = cls._services.get(provider)
        if not service_class:
            raise ValueError(f"El proveedor '{provider}' no está soportado")
        return service_class()

