"""
Almacén de historial de conversaciones para ventana de contexto.

Almacena mensajes por conversation_id en memoria.
Formato interno: list[{"role": "user"|"assistant", "content": str}]
"""
from typing import Optional

# conversation_id -> list de mensajes {role, content}
_store: dict[str, list[dict]] = {}


def get_history(conversation_id: str) -> list[dict]:
    """Devuelve el historial de mensajes de una conversación."""
    return _store.get(conversation_id, []).copy()


def append_messages(conversation_id: str, messages: list[dict]) -> None:
    """Añade mensajes al historial. Crea la conversación si no existe."""
    if conversation_id not in _store:
        _store[conversation_id] = []
    _store[conversation_id].extend(messages)


def clear_conversation(conversation_id: str) -> None:
    """Borra el historial de una conversación (para tests o reinicio)."""
    _store.pop(conversation_id, None)
