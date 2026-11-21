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
            raise ValueError("Answer choices must have unique values.")
        if self.tipo == "desarrollo":
            if self.alternativas or self.respuesta_correcta is not None:
                raise ValueError("Open-ended questions require an empty alternativas list and a null respuesta_correcta.")
        elif not self.alternativas:
            raise ValueError("Closed-ended questions require answer choices.")
        if self.tipo == "verdadero_falso" and len(self.alternativas) != 2:
            raise ValueError("True/false questions require two answer choices.")
        if self.respuesta_correcta is not None and self.tipo != "emparejamiento":
            if (type(self.respuesta_correcta), self.respuesta_correcta) not in values:
                raise ValueError("The correct answer must identify an answer choice.")
        return self


class Questionnaire(StrictModel):
    titulo: str = Field(min_length=1)
    idioma: str = Field(pattern=r"^[a-z]{2}$", description="ISO 639-1 language code: es, it, en, etc.")
    total_items: int = Field(ge=0)
    items: list[Item]

    @model_validator(mode="after")
    def consistent_items(self):
        if self.total_items != len(self.items):
            raise ValueError("total_items does not match the number of items.")
        numbers = [item.numero for item in self.items]
        if len(numbers) != len(set(numbers)):
            raise ValueError("Question numbers must be unique.")
        return self
