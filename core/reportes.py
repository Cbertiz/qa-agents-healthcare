"""Genera el reporte legible a partir del resultado. Lo hace código, no la IA:
es gratis, instantáneo y no puede inventar nada."""
from core.modelos import ResultadoAnalisis
from core.verificacion import estado_cita

ICONO_TIPO = {
    "evidencia_no_encontrada": "🔍",
    "evidencia_insuficiente": "🔍",
    "incoherencia": "⚖️",
    "formato": "📝",
}


MARCAS = {
    "ok": "✅ verificada",
    "corta": "⚠️ **cita demasiado corta para verificar**",
    "no_encontrada": "⚠️ **no encontrada en la story**",
}


def _marca(cita: str, texto: str) -> str:
    return MARCAS[estado_cita(cita, texto)]


def _celda(texto: str) -> str:
    return texto.replace("|", "\\|").replace("\n", " ")


def render_markdown(r: ResultadoAnalisis) -> str:
    a, s = r.analisis, r.story
    txt = s.texto_original
    out: list[str] = []

    out += [f"# Análisis de requerimientos: {s.id} — {s.titulo}", "",
            f"> Generado por IA (`{r.modelo}`, prompt `{r.version_prompt}`) el {r.fecha}. "
            "**Requiere revisión humana antes de usarse.**", ""]

    # Veredicto
    estado = "✅ Lista para desarrollo" if a.veredicto.lista_para_desarrollo else "❌ No lista para desarrollo"
    bloq = sum(x.bloqueante for x in a.ambiguedades)
    out += ["## Veredicto", "", f"**{estado}**", "", a.veredicto.resumen, ""]
    if any(al.tipo == "incoherencia" for al in r.alertas):
        out += ["> ⚠️ **La verificación automática encontró incoherencias en este veredicto.** "
                "Revisá la sección de verificación antes de confiar en él.", ""]
    out += [
            f"| Ambigüedades | Bloqueantes | Criterios faltantes | Riesgos | Escenarios |",
            f"|---|---|---|---|---|",
            f"| {len(a.ambiguedades)} | {bloq} | {len(a.criterios_faltantes)} | {len(a.riesgos)} | {len(a.gherkin)} |",
            ""]

    # Verificación
    out += ["## Verificación automática", "",
            f"- Evidencias verificadas en el texto: **{r.evidencias_verificadas} de {r.evidencias_totales}**",
            f"- Alertas: **{len(r.alertas)}**"]
    for al in r.alertas:
        out.append(f"  - {ICONO_TIPO[al.tipo]} `{al.tipo}`: {al.detalle}")
    out.append("")

    out += ["## Resumen de la story", "", a.resumen, ""]

    # Ambigüedades
    out += ["## Ambigüedades", ""]
    if not a.ambiguedades:
        out += ["_No se detectaron ambigüedades._", ""]
    orden = sorted(a.ambiguedades, key=lambda x: not x.bloqueante)
    for i, amb in enumerate(orden, 1):
        etiqueta = " 🔴 Bloqueante" if amb.bloqueante else ""
        out += [f"### {i}. {amb.descripcion}{etiqueta}", "",
                f"- **Evidencia:** \"{amb.evidencia}\" — {_marca(amb.evidencia, txt)}",
                f"- **Pregunta para el PO:** {amb.pregunta_para_po}", ""]

    # Criterios faltantes
    out += ["## Criterios de aceptación faltantes", ""]
    if not a.criterios_faltantes:
        out += ["_No se detectaron criterios faltantes._", ""]
    for i, cf in enumerate(a.criterios_faltantes, 1):
        out += [f"{i}. **{cf.descripcion}** — {cf.justificacion}"]
    out.append("")

    # Riesgos
    out += ["## Riesgos (ordenados por prioridad = impacto × probabilidad)", ""]
    if not a.riesgos:
        out += ["_No se detectaron riesgos._", ""]
    for i, rg in enumerate(sorted(a.riesgos, key=lambda x: x.prioridad, reverse=True), 1):
        out += [f"### {i}. {rg.descripcion} — Prioridad {rg.prioridad}/9", "",
                f"- **Impacto:** {rg.impacto}/3 · **Probabilidad (estimada):** {rg.probabilidad}/3",
                f"- **Evidencia:** \"{rg.evidencia}\" — {_marca(rg.evidencia, txt)}",
                f"- **Justificación:** {rg.justificacion}", ""]

    # Gherkin
    out += ["## Propuesta de criterios en Gherkin", ""]
    for esc in a.gherkin:
        out += [f"### {esc.titulo}", "",
                f"Criterio de origen: \"{esc.criterio_origen}\" — {_marca(esc.criterio_origen, txt)}", "",
                "```gherkin", f"Escenario: {esc.titulo}"]
        out += [f"  {p}" for p in esc.pasos]
        out += ["```", ""]
        if esc.supuestos:
            out += ["**Supuestos a validar con el PO** (no están en la story):", ""]
            out += [f"- {sup}" for sup in esc.supuestos]
            out.append("")

    # INVEST
    out += ["## Evaluación INVEST", "", "| Criterio | Cumple | Justificación |", "|---|---|---|"]
    for ev in a.invest:
        out.append(f"| {ev.criterio} | {'✅' if ev.cumple else '❌'} | {_celda(ev.justificacion)} |")
    out.append("")

    # Checklist humano
    out += ["## Checklist de revisión humana", "",
            "- [ ] Revisé cada hallazgo y marqué los falsos positivos",
            "- [ ] Revisé las alertas de verificación automática",
            "- [ ] Validé los supuestos del Gherkin con el PO",
            "- [ ] Confirmo o corrijo el veredicto", ""]
    return "\n".join(out)
