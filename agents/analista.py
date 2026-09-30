"""Agente 1: Analista de requerimientos.

Flujo: fuente -> IA -> validación del contrato -> verificación por código -> reportes.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # permite correrlo con: python agents\analista.py

from pydantic import ValidationError  # noqa: E402

from core.fuentes import leer_stories_md  # noqa: E402
from core.llm import MODELO, generar_json  # noqa: E402
from core.modelos import AnalisisStory, ResultadoAnalisis, Story  # noqa: E402
from core.reportes import render_markdown  # noqa: E402
from core.verificacion import verificar  # noqa: E402

VERSION_PROMPT = "analista-v2"
STORIES = ROOT / "stories"
SALIDA_JSON = ROOT / "output" / "analisis"
SALIDA_MD = ROOT / "output" / "reportes"

REGLAS = """Sos un QA Analyst senior. Analizás una user story ANTES de que se desarrolle.

REGLAS DE PRECISIÓN (obligatorias):
1. Basate solo en lo que dice la story. No inventes reglas de negocio.
2. Cada campo "evidencia" y "criterio_origen" debe ser un fragmento COPIADO TEXTUALMENTE de la story,
   de al menos 3 palabras, sin parafrasear ni corregir. Se verifica automáticamente contra el texto.
3. Si falta información, registrala como ambigüedad. Nunca la asumas.
4. En Gherkin, todo lo que agregues y no esté en la story va en "supuestos".
5. La probabilidad de un riesgo es una estimación: justificala. El impacto se basa en el negocio.
6. Preferí pocos hallazgos sólidos a muchos débiles. No rellenes listas: una lista vacía es válida.
7. No escribas casos de prueba ni datos de prueba: eso lo hace otro agente.
8. Evaluá los 6 criterios INVEST exactamente una vez, con estos nombres:
   Independiente, Negociable, Valiosa, Estimable, Pequeña, Testeable.
9. El veredicto debe ser coherente: si hay una ambigüedad bloqueante o falla un criterio INVEST,
   la story NO está lista para desarrollo.

Respondé SOLO con un JSON válido que cumpla este esquema:
"""
SYSTEM_PROMPT = REGLAS + json.dumps(AnalisisStory.model_json_schema(), ensure_ascii=False)


def construir_mensaje(story: Story) -> str:
    return f"story_id: {story.id}\n\n{story.texto_original}"


def analizar(story: Story, intentos: int = 3) -> AnalisisStory:
    """Pide el análisis y lo valida contra el contrato. Si no cumple,
    le devuelve los errores a la IA para que corrija."""
    mensaje = construir_mensaje(story)
    for intento in range(1, intentos + 1):
        texto = generar_json(SYSTEM_PROMPT, mensaje)
        texto = texto.strip().removeprefix("```json").removesuffix("```").strip()
        try:
            return AnalisisStory.model_validate_json(texto)
        except ValidationError as e:
            if intento == intentos:
                raise
            print(f"  [validación] la respuesta no cumple el contrato, reintento {intento}...")
            mensaje = (construir_mensaje(story)
                       + f"\n\nTu respuesta anterior no cumplió el esquema:\n{e}\n"
                         "Devolvé el JSON completo corregido.")
    raise RuntimeError("inalcanzable")


def procesar(story: Story) -> ResultadoAnalisis:
    analisis = analizar(story)
    alertas, verificadas, totales = verificar(analisis, story)
    return ResultadoAnalisis(
        story=story, analisis=analisis, alertas=alertas,
        evidencias_verificadas=verificadas, evidencias_totales=totales,
        modelo=MODELO, version_prompt=VERSION_PROMPT,
        fecha=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


def main():
    SALIDA_JSON.mkdir(parents=True, exist_ok=True)
    SALIDA_MD.mkdir(parents=True, exist_ok=True)
    stories = leer_stories_md(STORIES)
    if not stories:
        print(f"No hay stories con formato US-*.md en {STORIES}")
        return

    for story in stories:
        print(f"Analizando {story.id} ({story.titulo})...")
        try:
            r = procesar(story)
        except Exception as e:  # una story fallida no frena a las demás
            print(f"  [ERROR] {story.id}: {type(e).__name__}: {e}")
            continue

        (SALIDA_JSON / f"{story.id}.json").write_text(
            r.model_dump_json(indent=2), encoding="utf-8")
        (SALIDA_MD / f"{story.id}.md").write_text(render_markdown(r), encoding="utf-8")

        a = r.analisis
        estado = "LISTA" if a.veredicto.lista_para_desarrollo else "NO LISTA"
        bloq = sum(x.bloqueante for x in a.ambiguedades)
        print(f"  [OK] {estado} | ambigüedades: {len(a.ambiguedades)} (bloqueantes: {bloq}) | "
              f"riesgos: {len(a.riesgos)} | escenarios: {len(a.gherkin)} | "
              f"evidencias verificadas: {r.evidencias_verificadas}/{r.evidencias_totales} | "
              f"alertas: {len(r.alertas)}")
        print(f"       Reporte: output/reportes/{story.id}.md")


if __name__ == "__main__":
    main()
