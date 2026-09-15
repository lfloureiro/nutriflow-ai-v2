import uuid
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.nutrition_constraint import NutritionConstraint


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def test_nutrition_plan_api_lifecycle_and_effective_plan(db_session: Session) -> None:
    app.dependency_overrides[get_db] = _override_db(db_session)

    try:
        with TestClient(app) as client:
            family_response = client.post(
                "/api/families",
                json={"name": "Nutrition Plan API Family", "timezone": "Europe/Lisbon"},
            )
            assert family_response.status_code == 201
            family_id = family_response.json()["id"]

            person_response = client.post(
                f"/api/families/{family_id}/persons",
                json={
                    "first_name": "API",
                    "last_name": "Plan",
                    "birth_date": "1985-01-01",
                    "preferred_locale": "pt-PT",
                    "timezone": "Europe/Lisbon",
                },
            )
            assert person_response.status_code == 201
            person_id = person_response.json()["id"]

            plan_response = client.post(
                f"/api/persons/{person_id}/nutrition-plans",
                json={
                    "title": "Nutritionist plan",
                    "source_type": "nutritionist",
                    "source_name": "Nutritionist Test",
                    "source_reference": "document:test",
                    "original_text": "Protein >= 50 g at lunch",
                    "status": "draft",
                    "valid_from": date(2026, 9, 1).isoformat(),
                },
            )
            assert plan_response.status_code == 201
            plan = plan_response.json()
            plan_id = plan["id"]
            assert plan["version"] == 1
            assert plan["status"] == "draft"

            constraint = NutritionConstraint(
                person_id=uuid.UUID(person_id),
                constraint_type="nutrient_target",
                target_type="nutrient",
                target_key="protein",
                operator="min",
                value_min=Decimal("50"),
                unit="g",
                severity="required",
                is_mandatory=True,
                source="nutritionist",
                source_name="Nutritionist Test",
            )
            db_session.add(constraint)
            db_session.commit()

            rule_response = client.post(
                f"/api/persons/{person_id}/nutrition-plans/{plan_id}/rules",
                json={
                    "rule_kind": "constraint",
                    "reference_id": str(constraint.id),
                    "meal_type": "lunch",
                    "priority": 200,
                    "source_statement": "Protein >= 50 g at lunch",
                },
            )
            assert rule_response.status_code == 201
            assert rule_response.json()["reference_id"] == str(constraint.id)

            guideline_response = client.post(
                f"/api/persons/{person_id}/nutrition-plans/{plan_id}/guidelines",
                json={
                    "guideline_type": "qualitative",
                    "target_type": "food_group",
                    "target_key": "vegetables",
                    "description": "Prefer vegetables at lunch",
                    "meal_type": "lunch",
                },
            )
            assert guideline_response.status_code == 201

            activation_response = client.patch(
                f"/api/persons/{person_id}/nutrition-plans/{plan_id}",
                json={"status": "active"},
            )
            assert activation_response.status_code == 200
            assert activation_response.json()["status"] == "active"

            immutable_response = client.patch(
                f"/api/persons/{person_id}/nutrition-plans/{plan_id}",
                json={"title": "Should fail"},
            )
            assert immutable_response.status_code == 422

            effective_response = client.get(
                f"/api/persons/{person_id}/effective-nutrition-plan",
                params={"on_date": "2026-09-15", "meal_type": "lunch"},
            )
            assert effective_response.status_code == 200
            effective = effective_response.json()
            assert effective["active_plans"][0]["id"] == plan_id
            assert effective["numeric_rules"][0]["target_key"] == "protein"
            assert effective["numeric_rules"][0]["is_mandatory"] is True
            assert effective["guidelines"][0]["target_key"] == "vegetables"

            version_response = client.post(
                f"/api/persons/{person_id}/nutrition-plans/{plan_id}/versions",
                json={
                    "title": "Nutritionist plan v2",
                    "valid_from": "2026-09-20",
                },
            )
            assert version_response.status_code == 201
            version = version_response.json()
            assert version["version"] == 2
            assert len(version["rules"]) == 1
            assert len(version["guidelines"]) == 1

            v2_activation = client.patch(
                f"/api/persons/{person_id}/nutrition-plans/{version['id']}",
                json={"status": "active"},
            )
            assert v2_activation.status_code == 200

            plans_response = client.get(f"/api/persons/{person_id}/nutrition-plans")
            assert plans_response.status_code == 200
            statuses = {item["version"]: item["status"] for item in plans_response.json()}
            assert statuses == {1: "superseded", 2: "active"}

            before_v2_response = client.get(
                f"/api/persons/{person_id}/effective-nutrition-plan",
                params={"on_date": "2026-09-19", "meal_type": "lunch"},
            )
            assert before_v2_response.status_code == 200
            assert before_v2_response.json()["active_plans"][0]["id"] == plan_id

            from_v2_response = client.get(
                f"/api/persons/{person_id}/effective-nutrition-plan",
                params={"on_date": "2026-09-20", "meal_type": "lunch"},
            )
            assert from_v2_response.status_code == 200
            assert from_v2_response.json()["active_plans"][0]["id"] == version["id"]

    finally:
        app.dependency_overrides.clear()
