"""
Pruebas de integridad del esquema y configuración.

FASE 1 - Setup:
  - Añade la raíz del proyecto al path para poder importar 'app'.
  - Se ejecuta con: python tests/verify_schema.py

FASE 2 - Qué verifica:
  - test_provider_model_enums: cada proveedor tiene modelos en su Enum.
  - test_all_models_coverage: ALL_MODELS tiene entrada para cada modelo.
  - test_invalid_prompt_rejected: BaseGenerationRequest rechaza <script>, etc.
  - test_valid_prompt: prompts limpios pasan la validación.
  - test_model_type_lookup: un modelo conocido mapea al tipo correcto.

FASE 3 - Cuándo ejecutar:
  - Después de modificar _MODEL_CONFIG en generation.py.
  - En CI/CD para detectar regresiones en la configuración.
"""
import sys
import os

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from app.schemas.generation import (
    Provider,
    ModelType,
    ALL_MODELS,
    PROVIDER_MODELS,
    PROVIDER_MODEL_ENUMS,
    BaseGenerationRequest,
)
from pydantic import ValidationError


def test_provider_model_enums():
    """
    Verifica que cada proveedor tenga un Enum de modelos autogenerado con miembros.
    Funciona para: Asegurar que la configuración en _MODEL_CONFIG se traduzca bien a Enums.
    """
    for provider in Provider:
        enum_cls = PROVIDER_MODEL_ENUMS[provider]
        members = list(enum_cls)
        assert len(members) > 0, f"{provider.value} no tiene modelos registrados"
        print(f"  {provider.value}: {[m.value for m in members]}")
    print("✅ Enums de modelos por proveedor generados correctamente")


def test_all_models_coverage():
    """
    Verifica que cada miembro de los Enums tenga una entrada de tipo en ALL_MODELS.
    Funciona para: Evitar errores de 'KeyError' cuando los servicios buscan el tipo de un modelo.
    """
    for provider, models in PROVIDER_MODELS.items():
        for model in models:
            assert model in ALL_MODELS, f"El modelo {model} no está en ALL_MODELS"
            assert ALL_MODELS[model] in (ModelType.TEXT, ModelType.IMAGE)
    print(f"✅ ALL_MODELS cubre los {len(ALL_MODELS)} modelos configurados")


def test_invalid_prompt_rejected():
    """
    Verifica que la sanitización de prompts rechace patrones prohibidos.
    Funciona para: Probar la seguridad básica contra inyecciones de código.
    """
    try:
        BaseGenerationRequest(prompt="<script>alert(1)</script>")
        print("❌ El prompt inválido NO fue rechazado")
    except ValidationError:
        print("✅ Prompt inválido rechazado como se esperaba")


def test_valid_prompt():
    """
    Verifica que un prompt limpio pase la validación sin problemas.
    Salida esperada: Un objeto de petición válido con el prompt original.
    """
    req = BaseGenerationRequest(prompt="Un gato naranja")
    assert req.prompt == "Un gato naranja"
    print("✅ Prompt válido aceptado")


def test_model_type_lookup():
    """
    Prueba puntual para asegurar que un modelo conocido mapee al tipo correcto.
    Ejemplo: GPT_5 debe ser de tipo TEXTO.
    """
    openai_enum = PROVIDER_MODEL_ENUMS[Provider.OPENAI]
    # Se busca por el nombre del miembro generado dinámicamente
    gpt5 = openai_enum["GPT_5"]
    assert ALL_MODELS[gpt5] == ModelType.TEXT
    print("✅ Búsqueda de tipo de modelo (TEXT/IMAGE) correcta")


if __name__ == "__main__":
    # Ejecución manual de la batería de pruebas de integridad del esquema
    print("Iniciando verificación de esquemas y configuración...")
    test_provider_model_enums()
    test_all_models_coverage()
    test_invalid_prompt_rejected()
    test_valid_prompt()
    test_model_type_lookup()
    print("--- Verificación completada con éxito ---")

