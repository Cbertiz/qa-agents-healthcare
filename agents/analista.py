"""Agente 1: Analista de requerimientos.
Lee user stories de /stories y detecta ambigüedades, criterios faltantes y riesgos.
Usa la API gratuita de Gemini (Google AI Studio)."""
import json
import os
from pathlib import Path
from google import genai
from google.genai import types

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
ROOT = Path(__file__).resolve().parent.parent
STORIES = ROOT / "stories"
OUTPUT = ROOT / "output" / "analisis"

SYSTEM_PROMPT = """Sos un QA Analyst senior. Analizás user stories antes de que se escriban tests.
Para cada story devolvé SOLO un JSON válido, sin texto extra ni backticks, con esta forma:
{
  "story_id": "...",
  "ambiguedades": [{"texto": "...", "pregunta_para_po": "..."}],
  "criterios_faltantes": ["..."],
  "riesgos": [{"descripcion": "...", "severidad": "alta|media|baja"}],
  "testeable": true,
  "confianza": 0.0
}
No inventes reglas de negocio que no estén en la story: si falta información, marcala como ambigüedad."""

client = genai.Client()  # lee GEMINI_API_KEY del entorno


def analizar(story_path: Path) -> dict:
    story = story_path.read_text(encoding="utf-8")
    resp = client.models.generate_content(
        model=MODEL,
        contents=f"story_id: {story_path.stem}\n\n{story}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )
    texto = resp.text.strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(texto)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for path in sorted(STORIES.glob("*.md")):
        try:
            resultado = analizar(path)
        except json.JSONDecodeError:
            print(f"[ERROR] {path.name}: el modelo no devolvió JSON válido")
            continue
        (OUTPUT / f"{path.stem}.json").write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] {path.name}: {len(resultado['ambiguedades'])} ambigüedades, "
              f"{len(resultado['riesgos'])} riesgos")


if __name__ == "__main__":
    main()
