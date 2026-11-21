from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Alternative(StrictModel):
    valor: int | str
    texto: str = Field(min_length=1)


class Item(StrictModel):
    numero: int = Field(ge=1)
    enunciado: str = Field(min_length=1)
    tipo: Literal["escala_likert", "seleccion_multiple", "verdadero_falso", "desarrollo", "emparejamiento"]
    alternativas: list[Alternative]
    respuesta_correcta: int | str | dict[str, str] | None

    @model_validator(mode="after")
    def consistent_answers(self):
        values = [(type(a.valor), a.valor) for a in self.alternativas]
        if len(values) != len(set(values)):
            raise ValueError("Las alternativas deben tener valores únicos.")
        if self.tipo == "desarrollo":
            if self.alternativas or self.respuesta_correcta is not None:
                raise ValueError("Desarrollo requiere alternativas vacías y respuesta_correcta null.")
        elif not self.alternativas:
            raise ValueError("Los ítems cerrados requieren alternativas.")
        if self.tipo == "verdadero_falso" and len(self.alternativas) != 2:
            raise ValueError("Verdadero/falso requiere dos alternativas.")
        if self.respuesta_correcta is not None and self.tipo != "emparejamiento":
            if (type(self.respuesta_correcta), self.respuesta_correcta) not in values:
                raise ValueError("La respuesta correcta debe identificar una alternativa.")
        return self


class Questionnaire(StrictModel):
    titulo: str = Field(min_length=1)
    idioma: str = Field(pattern=r"^[a-z]{2}$", description="Código ISO 639-1: es, it, en, etc.")
    total_items: int = Field(ge=0)
    items: list[Item]

    @model_validator(mode="after")
    def consistent_items(self):
        if self.total_items != len(self.items):
            raise ValueError("total_items no coincide con items.")
        numbers = [item.numero for item in self.items]
        if len(numbers) != len(set(numbers)):
            raise ValueError("Los números de ítem deben ser únicos.")
        return self
