from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.family import Family
from app.models.person import Person


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def _person(db_session: Session) -> Person:
    family = Family(name="Import API Family", timezone="Europe/Lisbon")
    person = Person(
        family=family,
        first_name="API",
        last_name="Importer",
        birth_date=date(1988, 2, 5),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    db_session.add(person)
    db_session.commit()
    return person


def test_nutrition_plan_import_api_review_apply_and_activate(db_session: Session) -> None:
    person = _person(db_session)
    app.dependency_overrides[get_db] = _override_db(db_session)

    try:
        with TestClient(app) as client:
            create_response = client.post(
                f"/api/persons/{person.id}/nutrition-plan-imports",
                json={
                    "title": "Plano importado",
                    "source_type": "nutritionist",
                    "source_name": "Nutricionista API",
                    "source_text": (
                        "Proteína 50 g ao almoço\n"
                        "Peixe pelo menos 3 vezes por semana\n"
                        "Preferir salada ao almoço"
                    ),
                    "valid_from": "2026-09-15",
                },
            )
            assert create_response.status_code == 201
            import_data = create_response.json()
            import_id = import_data["id"]
            plan_id = import_data["nutrition_plan_id"]
            assert import_data["status"] == "review"
            assert import_data["nutrition_plan"]["status"] == "draft"
            assert len(import_data["proposals"]) == 3

            early_apply = client.post(
                f"/api/persons/{person.id}/nutrition-plan-imports/{import_id}/apply"
            )
            assert early_apply.status_code == 422

            qualitative = next(
                proposal
                for proposal in import_data["proposals"]
                if proposal["proposal_type"] == "qualitative_guideline"
            )
            invalid_edit = client.patch(
                (
                    f"/api/persons/{person.id}/nutrition-plan-imports/{import_id}"
                    f"/proposals/{qualitative['id']}"
                ),
                json={"proposal_type": "numeric_rule"},
            )
            assert invalid_edit.status_code == 422

            after_invalid_edit = client.get(
                f"/api/persons/{person.id}/nutrition-plan-imports/{import_id}"
            )
            assert after_invalid_edit.status_code == 200
            persisted_qualitative = next(
                proposal
                for proposal in after_invalid_edit.json()["proposals"]
                if proposal["id"] == qualitative["id"]
            )
            assert persisted_qualitative["proposal_type"] == "qualitative_guideline"

            for proposal in import_data["proposals"]:
                patch_response = client.patch(
                    (
                        f"/api/persons/{person.id}/nutrition-plan-imports/{import_id}"
                        f"/proposals/{proposal['id']}"
                    ),
                    json={"confirmation_status": "confirmed"},
                )
                assert patch_response.status_code == 200
                assert patch_response.json()["confirmation_status"] == "confirmed"

            apply_response = client.post(
                f"/api/persons/{person.id}/nutrition-plan-imports/{import_id}/apply"
            )
            assert apply_response.status_code == 200
            applied = apply_response.json()
            assert applied["status"] == "applied"
            assert applied["nutrition_plan"]["status"] == "draft"
            assert all(
                proposal["nutrition_plan_rule_id"] is not None
                or proposal["nutrition_plan_guideline_id"] is not None
                for proposal in applied["proposals"]
            )

            plan_response = client.get(
                f"/api/persons/{person.id}/nutrition-plans/{plan_id}"
            )
            assert plan_response.status_code == 200
            plan = plan_response.json()
            assert len(plan["rules"]) == 1
            assert len(plan["guidelines"]) == 2

            activate_response = client.patch(
                f"/api/persons/{person.id}/nutrition-plans/{plan_id}",
                json={"status": "active"},
            )
            assert activate_response.status_code == 200
            assert activate_response.json()["status"] == "active"

            effective_response = client.get(
                f"/api/persons/{person.id}/effective-nutrition-plan",
                params={"on_date": "2026-09-15", "meal_type": "lunch"},
            )
            assert effective_response.status_code == 200
            effective = effective_response.json()
            assert any(
                rule["target_key"] == "protein"
                for rule in effective["numeric_rules"]
            )
            assert any(
                guideline["target_key"] == "fish"
                for guideline in effective["guidelines"]
            )

            edit_after_apply = client.patch(
                (
                    f"/api/persons/{person.id}/nutrition-plan-imports/{import_id}"
                    f"/proposals/{applied['proposals'][0]['id']}"
                ),
                json={"review_notes": "late edit"},
            )
            assert edit_after_apply.status_code == 422
    finally:
        app.dependency_overrides.clear()
