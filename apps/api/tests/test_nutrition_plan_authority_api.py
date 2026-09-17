from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def test_effective_nutrition_plan_api_exposes_authority_state(
    db_session: Session,
) -> None:
    app.dependency_overrides[get_db] = _override_db(db_session)

    try:
        with TestClient(app) as client:
            family_response = client.post(
                "/api/families",
                json={
                    "name": "Authority API Family",
                    "timezone": "Europe/Lisbon",
                },
            )
            assert family_response.status_code == 201
            family_id = family_response.json()["id"]

            person_response = client.post(
                f"/api/families/{family_id}/persons",
                json={
                    "first_name": "Authority",
                    "last_name": "Tester",
                    "birth_date": "1985-01-01",
                    "preferred_locale": "pt-PT",
                    "timezone": "Europe/Lisbon",
                },
            )
            assert person_response.status_code == 201
            person_id = person_response.json()["id"]

            effective_response = client.get(
                f"/api/persons/{person_id}/effective-nutrition-plan",
                params={"on_date": "2026-09-17", "meal_type": "dinner"},
            )
            assert effective_response.status_code == 200
            authority = effective_response.json()["nutrition_plan_authority"]
            assert authority["state"] == "no_active_plan"
            assert authority["active_plans"] == []
            assert authority["plan_rule_ids"] == []
            assert authority["plan_guideline_ids"] == []
    finally:
        app.dependency_overrides.clear()
