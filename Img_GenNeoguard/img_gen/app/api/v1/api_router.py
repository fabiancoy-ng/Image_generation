"""
Router principal de la API v1.

FASE 1 - Agrupación:
  - Centraliza todos los dominios (generation, etc.) bajo un solo router.
  - Se monta en main.py con el prefijo /api/v1, así las rutas quedan como
    /api/v1/generation/openai, /api/v1/generation/models, etc.

FASE 2 - Tags:
  - El tag "generation" agrupa los endpoints en la documentación Swagger
    para una navegación más clara.
"""
from fastapi import APIRouter
from .endpoints import generation

api_router = APIRouter()

# Todas las rutas de generación (texto, imagen, edición) bajo /generation
api_router.include_router(generation.router, prefix="/generation", tags=["generation"])

