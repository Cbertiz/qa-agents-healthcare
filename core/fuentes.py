"""Fuentes de entrada. Cada fuente convierte su formato a un objeto Story.

Para agregar Jira más adelante: crear leer_ticket_jira() que devuelva Story.
El analista no cambia.
"""
from pathlib import Path

from core.modelos import Story


def _extraer_id(nombre: str) -> str:
    """'US-01-agendar-consulta' -> 'US-01'."""
    partes = nombre.split("-")
    return "-".join(partes[:2]) if len(partes) >= 2 else nombre


def leer_story_md(path: Path) -> Story:
    texto = path.read_text(encoding="utf-8")
    titulo = path.stem
    descripcion, criterios = [], []
    en_criterios = False

    for linea in texto.splitlines():
        l = linea.strip()
        if l.startswith("# "):
            titulo = l[2:].strip()
        elif l.startswith("## "):
            en_criterios = "criterio" in l.lower()
        elif en_criterios and l.startswith(("- ", "* ")):
            criterios.append(l[2:].strip())
        elif l and not en_criterios:
            descripcion.append(l)

    story_id = _extraer_id(path.stem)
    titulo = titulo.removeprefix(story_id).lstrip(" :-—")
    return Story(
        id=story_id,
        titulo=titulo,
        descripcion=" ".join(descripcion),
        criterios=criterios,
        texto_original=texto,
        fuente=f"archivo:{path.name}",
    )


def leer_stories_md(carpeta: Path, patron: str = "US-*.md") -> list[Story]:
    return [leer_story_md(p) for p in sorted(carpeta.glob(patron))]
