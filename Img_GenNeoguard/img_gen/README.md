# NeoGuard Image Generation API

API modular construida con FastAPI que actúa como **wrapper** para servicios de generación de imágenes y texto de múltiples proveedores (OpenAI y Google Gemini). Incluye generación desde texto, edición de imágenes con múltiples inputs, y una interfaz web para consumir la API.

---

## Índice

- [Arquitectura](#-arquitectura-y-componentes)
- [Flujo de datos](#-flujo-de-datos)
- [Endpoints](#-endpoints)
- [Configuración](#-configuración)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Pruebas](#-pruebas)

---

## 🚀 Arquitectura y Componentes

### 1. Núcleo (Core)

| Archivo | Propósito |
|---------|-----------|
| **`app/main.py`** | Punto de entrada. Monta FastAPI, CORS y el router principal. |
| **`app/core/config.py`** | Configuración global y API Keys. Lee desde `.env` vía `pydantic-settings`. |

### 2. Esquemas (`app/schemas/generation.py`)

**Fuente única de verdad** para modelos y proveedores:

- **`_MODEL_CONFIG`**: Diccionario maestro que define qué modelos ofrece cada proveedor y si son de texto o imagen.
- **Generación dinámica**: A partir de este diccionario se derivan automáticamente Enums para Swagger, listas de modelos y mapeos de tipo (TEXT/IMAGE).
- **Validación**: Sanitización de prompts para evitar patrones de inyección básicos.
- **Edición de imágenes**: Constantes para formatos permitidos (PNG, JPEG, GIF, WEBP) y modelos de edición (gpt-image-1.5, etc.).

### 3. Endpoints (`app/api/v1/`)

- **`api_router.py`**: Router principal que agrupa todos los dominios bajo `/api/v1`.
- **`endpoints/generation.py`**:
  - Endpoints dinámicos por proveedor (`POST /openai`, `POST /gemini`).
  - `GET /models`: Lista modelos disponibles.
  - `GET /edit-info`: Información para edición (formatos, límites).
  - `POST /openai/edit`: Edición de imágenes con múltiples inputs.

### 4. Capa de Servicios (`app/services/`)

| Archivo | Propósito |
|---------|-----------|
| **`factory.py`** | Patrón Factory: instancia el servicio correcto según el proveedor. |
| **`providers/base.py`** | Clase base abstracta. Define `generate()` y `resolve_model_type()`. |
| **`providers/openai_service.py`** | OpenAI: Chat Completions (texto), Images Generations (imágenes), Images Edits (edición). |
| **`providers/gemini_service.py`** | Google Gemini: texto e imagen (placeholder). |

### 5. Frontend (`static/`)

Los archivos de la interfaz web están agrupados en la carpeta `static/`:

| Archivo | Propósito |
|---------|-----------|
| **`static/index.html`** | Estructura: tabs Generar/Editar, formularios, área de resultado. |
| **`static/app.js`** | Lógica: carga modelos, envío de formularios, visualización de resultados. |
| **`static/style.css`** | Estilos: tema oscuro, glassmorphism, animaciones. |

FastAPI monta `static/` en la raíz (`/`) para servir la interfaz al iniciar el servidor.

---

## 🔄 Flujo de Datos

### Generación (texto o imagen)

1. **Request** → Usuario envía `POST /api/v1/generation/{provider}` con `prompt` y `model`.
2. **Validación** → FastAPI y Pydantic validan prompt y modelo.
3. **Factory** → `ServiceFactory.get_service(provider)` devuelve el servicio correcto.
4. **Enrutamiento** → El servicio usa `resolve_model_type()` para decidir si llama a Chat Completions o Images Generations.
5. **Response** → `GenerationResponse` con `content` (texto) o `image_base64` (imagen).

### Edición de imágenes

1. **Request** → Usuario envía `POST /api/v1/generation/openai/edit` con `prompt`, `model` y archivos de imagen.
2. **Validación** → Se comprueban extensiones (PNG, JPEG, GIF, WEBP) y límites (1–16 imágenes).
3. **Conversión** → Cada archivo se convierte a data URL base64 para la API de OpenAI.
4. **Llamada** → `OpenAIProviderService.edit_image()` llama a `POST /images/edits`.
5. **Response** → `GenerationResponse` con la imagen editada en Base64.

---

## 📡 Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Health check del servicio. |
| GET | `/api/v1/generation/models` | Lista modelos por proveedor. |
| GET | `/api/v1/generation/edit-info` | Formatos permitidos y modelos de edición. |
| POST | `/api/v1/generation/openai` | Generar texto o imagen con OpenAI. |
| POST | `/api/v1/generation/gemini` | Generar texto o imagen con Gemini. |
| POST | `/api/v1/generation/openai/edit` | Editar imágenes con OpenAI (1–16 inputs). |

**Formatos permitidos para edición:** PNG, JPEG, GIF, WEBP (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`).

---

## ⚙️ Configuración

1. Crear archivo `.env` en la raíz del proyecto:

```env
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```

2. Instalar dependencias e iniciar:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

3. Abrir la interfaz en `http://127.0.0.1:8000/` o la documentación en `http://127.0.0.1:8000/api/v1/openapi.json`.

---

## 📁 Estructura del Proyecto

```
img_gen/
├── app/
│   ├── main.py              # Entrada de la aplicación
│   ├── core/
│   │   └── config.py        # Configuración y variables de entorno
│   ├── schemas/
│   │   └── generation.py    # Modelos, enums, validaciones
│   ├── api/
│   │   └── v1/
│   │       ├── api_router.py
│   │       └── endpoints/
│   │           └── generation.py
│   └── services/
│       ├── factory.py
│       └── providers/
│           ├── base.py
│           ├── openai_service.py
│           └── gemini_service.py
├── static/                  # Interfaz web
│   ├── index.html
│   ├── app.js
│   └── style.css
├── tests/
│   └── verify_schema.py     # Pruebas de integridad del esquema
├── .env
└── README.md
```

---

## 🧪 Pruebas

Ejecutar verificación de esquemas:

```bash
python tests/verify_schema.py
```

Comprueba que:

- Los Enums de modelos se generan correctamente.
- `ALL_MODELS` cubre todos los modelos configurados.
- La sanitización de prompts rechaza patrones prohibidos.
- La búsqueda de tipo de modelo (TEXT/IMAGE) funciona.
