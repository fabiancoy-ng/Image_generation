"""
Punto de entrada de la aplicación NeoGuard Image Gen.

FASE 1 - Montaje de la app:
  - Crea la instancia FastAPI con título y ruta del esquema OpenAPI.
  - El esquema se expone en /api/v1/openapi.json para que clientes (Swagger, Postman)
    puedan descubrir los endpoints disponibles.

FASE 2 - CORS:
  - Permite que el frontend (index.html) consuma la API desde otro origen/puerto.
  - En producción conviene restringir allow_origins a dominios concretos.

FASE 3 - Rutas:
  - Incluye el router de la API v1 bajo el prefijo /api/v1.
  - El endpoint /health queda en la raíz para monitoreo rápido.

FASE 4 - Archivos estáticos:
  - Monta la carpeta static/ en la raíz para servir la interfaz web.
  - / sirve index.html, /style.css y /app.js se sirven desde static/.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import settings
from .api.v1.api_router import api_router

# Inicialización de la aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS: necesario porque el frontend (HTML estático) suele servirse desde otro puerto
# o dominio; sin esto el navegador bloquearía las peticiones fetch() por política same-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Con "*" no se puede usar True (especificación CORS)
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monta todas las rutas de la API v1 bajo /api/v1 (generation, etc.)
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
def health_check():
    """
    Health check para monitoreo y load balancers.
    Responde rápido sin depender de servicios externos (OpenAI, Gemini).
    """
    return {"status": "ok"}


# Archivos estáticos: debe ir al final para no interceptar /health ni /api/v1
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

