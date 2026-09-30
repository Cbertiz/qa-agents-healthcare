"""Acceso al modelo de IA. Es el único archivo que sabe que usamos Gemini.

Para cambiar de proveedor (Claude, OpenAI...) solo se modifica este archivo.
"""
import os
import time

from google import genai
from google.genai import errors, types

MODELO = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
_cliente = None


def _get_cliente() -> genai.Client:
    global _cliente
    if _cliente is None:
        _cliente = genai.Client()  # lee GEMINI_API_KEY del entorno
    return _cliente


def generar_json(system_prompt: str, mensaje: str, reintentos: int = 4) -> str:
    """Pide una respuesta JSON. Reintenta con espera progresiva si el servicio
    está saturado (503) o se superó el límite de pedidos (429)."""
    espera = 5
    for intento in range(1, reintentos + 1):
        try:
            resp = _get_cliente().models.generate_content(
                model=MODELO,
                contents=mensaje,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
            return resp.text or ""
        except errors.APIError as e:
            recuperable = e.code in (429, 500, 503)
            if not recuperable or intento == reintentos:
                raise
            print(f"  [reintento {intento}/{reintentos - 1}] el servicio respondió {e.code}, "
                  f"espero {espera}s...")
            time.sleep(espera)
            espera *= 2
    return ""
