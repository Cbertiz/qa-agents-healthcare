"""Contratos de datos: la forma exacta de lo que entra y sale de cada agente.

Si la IA devuelve algo que no cumple estos modelos, se detecta en el momento
en vez de romper más adelante en otro agente.
"""
from typing import Literal, get_args

from pydantic import BaseModel, Field, model_validator

CriterioInvest = Literal["Independiente", "Negociable", "Valiosa", "Estimable", "Pequeña", "Testeable"]
CRITERIOS_INVEST = get_args(CriterioInvest)


# ---------- Entrada normalizada (la produce cualquier fuente: .md, Jira, etc.) ----------

class Story(BaseModel):
    id: str
    titulo: str
    descripcion: str
    criterios: list[str]
    texto_original: str
    fuente: str


# ---------- Salida de la IA (validada contra este contrato) ----------

class Ambiguedad(BaseModel):
    descripcion: str = Field(description="Qué no está claro y por qué importa")
    evidencia: str = Field(description="Fragmento copiado TEXTUALMENTE de la story, sin parafrasear")
    pregunta_para_po: str
    bloqueante: bool = Field(description="true si impide desarrollar o testear sin una respuesta")


class CriterioFaltante(BaseModel):
    descripcion: str
    justificacion: str = Field(description="Por qué hace falta, basado en lo que sí dice la story")


class Riesgo(BaseModel):
    descripcion: str
    evidencia: str = Field(description="Fragmento copiado TEXTUALMENTE de la story, sin parafrasear")
    impacto: int = Field(ge=1, le=3, description="1=bajo, 2=medio, 3=alto")
    probabilidad: int = Field(ge=1, le=3, description="1=baja, 2=media, 3=alta. Es una estimación")
    justificacion: str

    @property
    def prioridad(self) -> int:
        # La calcula el código, no la IA.
        return self.impacto * self.probabilidad


class EscenarioGherkin(BaseModel):
    titulo: str
    criterio_origen: str = Field(description="Criterio de aceptación copiado TEXTUALMENTE de la story")
    pasos: list[str] = Field(description="Cada paso empieza con Dado, Cuando, Entonces, Y o Pero")
    supuestos: list[str] = Field(description="Todo lo que agregaste en los pasos y NO está en la story")


class EvaluacionInvest(BaseModel):
    criterio: CriterioInvest
    cumple: bool
    justificacion: str


class Veredicto(BaseModel):
    lista_para_desarrollo: bool
    resumen: str = Field(description="Una o dos oraciones con la conclusión principal")


class AnalisisStory(BaseModel):
    story_id: str
    resumen: str = Field(description="Qué pide la story, en una o dos oraciones")
    ambiguedades: list[Ambiguedad]
    criterios_faltantes: list[CriterioFaltante]
    riesgos: list[Riesgo]
    gherkin: list[EscenarioGherkin]
    invest: list[EvaluacionInvest]
    veredicto: Veredicto

    @model_validator(mode="after")
    def invest_completo(self):
        vistos = [e.criterio for e in self.invest]
        faltan = sorted(set(CRITERIOS_INVEST) - set(vistos))
        if faltan or len(vistos) != len(set(vistos)):
            raise ValueError(
                f"INVEST debe evaluar cada criterio exactamente una vez. Faltan: {faltan}")
        return self


# ---------- Resultado final (IA + verificaciones hechas por código) ----------

class Alerta(BaseModel):
    tipo: Literal["evidencia_no_encontrada", "evidencia_insuficiente", "incoherencia", "formato"]
    detalle: str


class ResultadoAnalisis(BaseModel):
    story: Story
    analisis: AnalisisStory
    alertas: list[Alerta]
    evidencias_verificadas: int
    evidencias_totales: int
    modelo: str
    version_prompt: str
    fecha: str
