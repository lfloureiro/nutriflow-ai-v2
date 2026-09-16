from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.person import Person
from app.schemas.nutrition_plan_import import NutritionPlanImportCreate
from app.services import nutrition_plan_ai_import
from app.services.nutrition_plan_ai_import import (
    NutritionPlanAIImportError,
    create_ai_nutrition_plan_import,
)


def _person(db_session: Session) -> Person:
    family = Family(name="AI Import Family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="AI",
        last_name="Tester",
        birth_date=date(1985, 6, 10),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    db_session.add(person)
    db_session.commit()
    return person


def _payload() -> NutritionPlanImportCreate:
    return NutritionPlanImportCreate(
        title="Plano da nutricionista",
        source_type="nutritionist",
        source_name="Dra. Teste",
        source_text="Ao pequeno-almoço consumir pelo menos 30 g de proteína. Preferir pão integral.",
        valid_from=date(2026, 9, 16),
    )


def test_ai_import_stays_draft_and_requires_human_review(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    person = _person(db_session)

    def fake_call(_: str):
        return (
            [
                {
                    "source_statement": "consumir pelo menos 30 g de proteína",
                    "proposal_type": "numeric_rule",
                    "target_type": "nutrient",
                    "target_key": "protein",
                    "operator": "min",
                    "value_min": 30,
                    "value_max": None,
                    "value_target": None,
                    "unit": "g",
                    "description": None,
                    "meal_type": "breakfast",
                    "period": None,
                    "minimum_occurrences": None,
                    "maximum_occurrences": None,
                    "severity": "required",
                    "is_mandatory": True,
                    "priority": 100,
                    "confidence": 0.97,
                    "parser_note": "Explicit numeric minimum.",
                },
                {
                    "source_statement": "Preferir pão integral",
                    "proposal_type": "qualitative_guideline",
                    "target_type": "food_category",
                    "target_key": "whole_grain_bread",
                    "operator": None,
                    "value_min": None,
                    "value_max": None,
                    "value_target": None,
                    "unit": None,
                    "description": "Preferir pão integral.",
                    "meal_type": None,
                    "period": None,
                    "minimum_occurrences": None,
                    "maximum_occurrences": None,
                    "severity": "advisory",
                    "is_mandatory": False,
                    "priority": 100,
                    "confidence": 0.88,
                    "parser_note": "Explicit qualitative preference.",
                },
            ],
            "Foram extraídas duas recomendações para revisão.",
            "test-model",
        )

    monkeypatch.setattr(nutrition_plan_ai_import, "_call_openai", fake_call)

    result = create_ai_nutrition_plan_import(db_session, person=person, data=_payload())

    assert result.status == "review"
    assert result.nutrition_plan.status == "draft"
    assert result.parser_name == "openai-responses"
    assert result.parser_version.endswith(":test-model")
    assert len(result.proposals) == 2
    assert all(item.confirmation_status == "proposed" for item in result.proposals)
    assert result.proposals[0].target_key == "protein"
    assert result.proposals[0].meal_type == "breakfast"
    assert result.proposals[0].is_mandatory is True


def test_ai_import_requires_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(NutritionPlanAIImportError, match="OPENAI_API_KEY"):
        nutrition_plan_ai_import._call_openai("Preferir legumes.")
