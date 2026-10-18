import json
from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.person import Person
from app.schemas.nutrition_plan_import import NutritionPlanImportCreate
from app.services import nutrition_plan_ai_import
from app.services.nutrition_plan_ai_import import (
    NutritionPlanAIImportError,
    build_chatgpt_nutrition_plan_prompt,
    create_ai_nutrition_plan_import,
    create_chatgpt_assisted_nutrition_plan_import,
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
    monkeypatch.setattr(nutrition_plan_ai_import.settings, "openai_api_key", None)
    with pytest.raises(NutritionPlanAIImportError, match="OPENAI_API_KEY"):
        nutrition_plan_ai_import._call_openai("Preferir legumes.")


def test_ai_import_uses_application_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return (
                b'{"output_text":"{\\\"proposals\\\":[{'
                b'\\\"source_statement\\\":\\\"Preferir legumes\\\",'
                b'\\\"proposal_type\\\":\\\"qualitative_guideline\\\",'
                b'\\\"target_type\\\":\\\"food_category\\\",'
                b'\\\"target_key\\\":\\\"vegetables\\\",'
                b'\\\"operator\\\":null,'
                b'\\\"value_min\\\":null,'
                b'\\\"value_max\\\":null,'
                b'\\\"value_target\\\":null,'
                b'\\\"unit\\\":null,'
                b'\\\"description\\\":\\\"Preferir legumes.\\\",'
                b'\\\"meal_type\\\":null,'
                b'\\\"period\\\":null,'
                b'\\\"minimum_occurrences\\\":null,'
                b'\\\"maximum_occurrences\\\":null,'
                b'\\\"severity\\\":\\\"advisory\\\",'
                b'\\\"is_mandatory\\\":false,'
                b'\\\"priority\\\":100,'
                b'\\\"confidence\\\":0.9,'
                b'\\\"parser_note\\\":null}],'
                b'\\\"summary\\\":\\\"Uma recomendacao.\\\"}"}'
            )

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        captured["payload"] = request.data
        return FakeResponse()

    monkeypatch.setattr(nutrition_plan_ai_import.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(
        nutrition_plan_ai_import.settings,
        "openai_base_url",
        "https://example.invalid/v1",
    )
    monkeypatch.setattr(
        nutrition_plan_ai_import.settings,
        "nutriflow_nutrition_plan_ai_model",
        "test-model",
    )
    monkeypatch.setattr(nutrition_plan_ai_import, "urlopen", fake_urlopen)

    proposals, summary, model = nutrition_plan_ai_import._call_openai("Preferir legumes.")

    assert model == "test-model"
    assert summary == "Uma recomendacao."
    assert proposals[0]["target_key"] == "vegetables"
    assert captured["url"] == "https://example.invalid/v1/responses"
    assert captured["authorization"] == "Bearer test-key"
    assert b'"model": "test-model"' in captured["payload"]

def test_chatgpt_prompt_contains_source_and_strict_json_contract() -> None:
    prompt = build_chatgpt_nutrition_plan_prompt(
        "Ao pequeno-almoço consumir pelo menos 30 g de proteína."
    )

    assert "SOURCE TEXT START" in prompt
    assert "30 g de proteína" in prompt
    assert "Return ONLY one JSON object" in prompt
    assert '"proposals"' in prompt
    assert '"summary"' in prompt
    assert "operator='exclude'" in prompt


def test_chatgpt_assisted_import_validates_pasted_json_and_stays_in_review(
    db_session: Session,
) -> None:
    person = _person(db_session)
    structured = {
        "proposals": [
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
            }
        ],
        "summary": "Uma recomendação estruturada para revisão.",
    }
    response_text = "```json\n" + json.dumps(structured, ensure_ascii=False) + "\n```"

    result = create_chatgpt_assisted_nutrition_plan_import(
        db_session,
        person=person,
        data=_payload(),
        response_text=response_text,
    )

    assert result.status == "review"
    assert result.nutrition_plan.status == "draft"
    assert result.parser_name == "chatgpt-assisted"
    assert result.parser_version.endswith("manual-chatgpt")
    assert len(result.proposals) == 1
    assert result.proposals[0].confirmation_status == "proposed"
    assert result.proposals[0].target_key == "protein"


def test_chatgpt_assisted_import_accepts_structured_exclusion(
    db_session: Session,
) -> None:
    person = _person(db_session)
    structured = {
        "proposals": [
            {
                "source_statement": "Evitar soja",
                "proposal_type": "numeric_rule",
                "target_type": "food_category",
                "target_key": "soy",
                "operator": "exclude",
                "value_min": None,
                "value_max": None,
                "value_target": None,
                "unit": None,
                "description": None,
                "meal_type": None,
                "period": None,
                "minimum_occurrences": None,
                "maximum_occurrences": None,
                "severity": "required",
                "is_mandatory": True,
                "priority": 100,
                "confidence": 0.99,
                "parser_note": "Explicit prohibition.",
            }
        ],
        "summary": "Uma exclusão estruturada para revisão.",
    }

    result = create_chatgpt_assisted_nutrition_plan_import(
        db_session,
        person=person,
        data=NutritionPlanImportCreate(
            title="Plano com exclusão",
            source_type="nutritionist",
            source_text="Evitar soja",
            valid_from=date(2026, 9, 16),
        ),
        response_text=json.dumps(structured, ensure_ascii=False),
    )

    assert len(result.proposals) == 1
    proposal = result.proposals[0]
    assert proposal.proposal_type == "numeric_rule"
    assert proposal.operator == "exclude"
    assert proposal.target_type == "food_category"
    assert proposal.target_key == "soy"
    assert proposal.unit is None
    assert proposal.value_min is None
    assert proposal.is_mandatory is True


def test_chatgpt_assisted_import_rejects_non_json_response(db_session: Session) -> None:
    person = _person(db_session)
    with pytest.raises(NutritionPlanAIImportError, match="not valid JSON"):
        create_chatgpt_assisted_nutrition_plan_import(
            db_session,
            person=person,
            data=_payload(),
            response_text="Aqui está a interpretação.",
        )

