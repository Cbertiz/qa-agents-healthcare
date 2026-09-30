"""Verificaciones determinísticas: controles hechos por código, sin IA.

Detectan posibles alucinaciones (citas que no existen en la story)
e incoherencias internas del análisis.
"""
import re
import unicodedata

from core.modelos import Alerta, AnalisisStory, Story

PALABRAS_GHERKIN = ("dado", "cuando", "entonces", "y ", "pero")
MIN_PALABRAS_EVIDENCIA = 3


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFC", texto).lower()
    texto = re.sub(r"[\"'“”‘’`*_#]", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip(" .,;:-")


def evidencia_existe(cita: str, texto: str) -> bool:
    cita_n = _normalizar(cita)
    return bool(cita_n) and cita_n in _normalizar(texto)


def estado_cita(cita: str, texto: str) -> str:
    """'ok', 'corta' o 'no_encontrada'."""
    if len(cita.split()) < MIN_PALABRAS_EVIDENCIA:
        return "corta"
    return "ok" if evidencia_existe(cita, texto) else "no_encontrada"


def _revisar_cita(cita: str, donde: str, story: Story, alertas: list[Alerta]) -> bool:
    estado = estado_cita(cita, story.texto_original)
    if estado == "corta":
        alertas.append(Alerta(tipo="evidencia_insuficiente",
                              detalle=f'{donde}: la cita "{cita}" es demasiado corta para verificarla'))
        return False
    if estado == "no_encontrada":
        alertas.append(Alerta(tipo="evidencia_no_encontrada",
                              detalle=f'{donde}: "{cita}" no aparece en la story (posible alucinación)'))
        return False
    return True


def verificar(analisis: AnalisisStory, story: Story) -> tuple[list[Alerta], int, int]:
    """Devuelve (alertas, evidencias_verificadas, evidencias_totales)."""
    alertas: list[Alerta] = []
    citas = (
        [(a.evidencia, f"Ambigüedad {i}") for i, a in enumerate(analisis.ambiguedades, 1)]
        + [(r.evidencia, f"Riesgo {i}") for i, r in enumerate(analisis.riesgos, 1)]
        + [(g.criterio_origen, f"Escenario {i}") for i, g in enumerate(analisis.gherkin, 1)]
    )
    verificadas = sum(_revisar_cita(c, donde, story, alertas) for c, donde in citas)

    # Coherencia del veredicto con el resto del análisis
    bloqueantes = [a for a in analisis.ambiguedades if a.bloqueante]
    invest_fallidos = [e.criterio for e in analisis.invest if not e.cumple]
    lista = analisis.veredicto.lista_para_desarrollo
    if lista and (bloqueantes or invest_fallidos):
        alertas.append(Alerta(tipo="incoherencia", detalle=(
            f"El veredicto dice 'lista para desarrollo' pero hay {len(bloqueantes)} ambigüedad(es) "
            f"bloqueante(s) y falla INVEST en: {invest_fallidos or 'ninguno'}")))
    if not lista and not bloqueantes and not invest_fallidos:
        alertas.append(Alerta(tipo="incoherencia", detalle=(
            "El veredicto dice 'no lista' pero no hay ambigüedades bloqueantes ni fallos INVEST")))

    if analisis.story_id != story.id:
        alertas.append(Alerta(tipo="incoherencia",
                              detalle=f"story_id '{analisis.story_id}' no coincide con '{story.id}'"))

    # Formato Gherkin
    for i, esc in enumerate(analisis.gherkin, 1):
        for paso in esc.pasos:
            if not paso.strip().lower().startswith(PALABRAS_GHERKIN):
                alertas.append(Alerta(tipo="formato",
                                      detalle=f'Escenario {i}: el paso "{paso}" no es Gherkin válido'))

    return alertas, verificadas, len(citas)
