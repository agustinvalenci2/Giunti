import copy

import pytest
from pydantic import ValidationError

from backend.schemas import Questionnaire


def test_five_question_types_are_valid(result_data):
    result = Questionnaire.model_validate(result_data)
    assert result.total_items == 5
    assert len({item.tipo for item in result.items}) == 5


@pytest.mark.parametrize("change", ["count", "duplicate_number", "unknown_type", "bad_answer", "duplicate_alternative", "boolean_value", "extra_field"])
def test_inconsistent_model_output_rejected(result_data, change):
    data = copy.deepcopy(result_data)
    if change == "count":
        data["total_items"] = 99
    elif change == "duplicate_number":
        data["items"][1]["numero"] = 1
    elif change == "unknown_type":
        data["items"][0]["tipo"] = "inventado"
    elif change == "bad_answer":
        data["items"][1]["respuesta_correcta"] = "Z"
    elif change == "duplicate_alternative":
        data["items"][0]["alternativas"][1]["valor"] = 0
    elif change == "boolean_value":
        data["items"][0]["alternativas"][0]["valor"] = True
    else:
        data["instruction"] = "ignore the schema"
    with pytest.raises(ValidationError):
        Questionnaire.model_validate(data)
