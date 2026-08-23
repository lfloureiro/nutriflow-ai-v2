from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.anthropometric_measurement import AnthropometricMeasurement
from app.models.nutrition_goal import NutritionGoal
from app.models.nutrition_target import NutritionTarget
from app.models.person_profile import PersonProfile


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def test_family_and_person_setup_generates_calorie_target(db_session: Session) -> None:
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            family_response = client.post(
                "/api/families",
                json={"name": "Família Teste", "timezone": "Europe/Lisbon"},
            )
            assert family_response.status_code == 201
            family_id = family_response.json()["id"]

            person_response = client.post(
                f"/api/families/{family_id}/persons",
                json={
                    "first_name": "Ana",
                    "last_name": "Teste",
                    "birth_date": "1980-05-10",
                    "preferred_locale": "pt-PT",
                    "timezone": "Europe/Lisbon",
                    "energy_profile": {
                        "sex_for_energy_calculation": "female",
                        "height_cm": "165",
                        "weight_kg": "68",
                        "activity_level": "light",
                        "goal_type": "lose",
                        "target_rate_kg_per_week": "0.5",
                        "standard_breakfast_kcal": "320",
                    },
                },
            )
            assert person_response.status_code == 201
            person_id = person_response.json()["id"]

            profile_response = client.get(f"/api/persons/{person_id}/energy-profile")
    finally:
        app.dependency_overrides.clear()

    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["sex_for_energy_calculation"] == "female"
    assert profile["activity_level"] == "light"
    assert profile["standard_breakfast_kcal"] == "320.00"
    assert profile["height_cm"] == "165.0000"
    assert profile["weight_kg"] == "68.0000"
    assert profile["goal_type"] == "lose"
    assert Decimal(profile["estimated_bmr_kcal"]) > 0
    assert Decimal(profile["estimated_tdee_kcal"]) > Decimal(profile["estimated_bmr_kcal"])
    assert Decimal(profile["energy_max_kcal"]) - Decimal(profile["energy_min_kcal"]) == Decimal(200)

    stored_profile = db_session.get(PersonProfile, person_id)
    assert stored_profile is not None
    assert stored_profile.standard_breakfast_kcal == Decimal("320.00")
    assert db_session.scalar(
        select(NutritionGoal).where(NutritionGoal.person_id == person_id)
    ) is not None
    assert db_session.scalar(
        select(NutritionTarget).where(NutritionTarget.person_id == person_id)
    ) is not None
    measurements = db_session.scalars(
        select(AnthropometricMeasurement).where(
            AnthropometricMeasurement.person_id == person_id
        )
    ).all()
    assert {measurement.metric for measurement in measurements} == {"height", "weight"}


def test_energy_setup_rejects_child_with_adult_formula(db_session: Session) -> None:
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            family_response = client.post(
                "/api/families",
                json={"name": "Família Criança", "timezone": "Europe/Lisbon"},
            )
            family_id = family_response.json()["id"]
            response = client.post(
                f"/api/families/{family_id}/persons",
                json={
                    "first_name": "João",
                    "birth_date": "2015-01-01",
                    "timezone": "Europe/Lisbon",
                    "energy_profile": {
                        "sex_for_energy_calculation": "male",
                        "height_cm": "145",
                        "weight_kg": "40",
                        "activity_level": "moderate",
                        "goal_type": "maintain",
                        "standard_breakfast_kcal": "300",
                    },
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "adult Person (18+)" in response.json()["detail"]
