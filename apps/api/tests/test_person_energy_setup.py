import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
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
            person_id_text = person_response.json()["id"]

            profile_response = client.get(f"/api/persons/{person_id_text}/energy-profile")
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

    person_id = uuid.UUID(person_id_text)
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


def test_person_energy_profile_update_preserves_discovery_and_versions_history(
    db_session: Session,
) -> None:
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            family = client.post(
                "/api/families",
                json={"name": "Família Perfil", "timezone": "Europe/Lisbon"},
            ).json()
            created = client.post(
                f"/api/families/{family['id']}/persons",
                json={
                    "first_name": "Luis",
                    "birth_date": "1973-06-01",
                    "timezone": "Europe/Lisbon",
                    "energy_profile": {
                        "sex_for_energy_calculation": "male",
                        "height_cm": "178",
                        "weight_kg": "104",
                        "activity_level": "sedentary",
                        "goal_type": "maintain",
                        "standard_breakfast_kcal": "350",
                    },
                    "meal_discovery": {
                        "meal_discovery_sources": ["shared_recipes"],
                        "restaurant_area": "Benfica",
                    },
                },
            )
            assert created.status_code == 201
            person_id = created.json()["id"]

            updated = client.patch(
                f"/api/persons/{person_id}",
                json={
                    "energy_profile": {
                        "sex_for_energy_calculation": "male",
                        "height_cm": "178",
                        "weight_kg": "101.5",
                        "activity_level": "light",
                        "goal_type": "lose",
                        "target_rate_kg_per_week": "0.4",
                        "standard_breakfast_kcal": "330",
                    }
                },
            )
            profile_after_weight = client.get(f"/api/persons/{person_id}/energy-profile")
            discovery = client.get(f"/api/persons/{person_id}/meal-discovery")

            activity_update = client.patch(
                f"/api/persons/{person_id}",
                json={
                    "energy_profile": {
                        "sex_for_energy_calculation": "male",
                        "height_cm": "178",
                        "weight_kg": "101.5",
                        "activity_level": "moderate",
                        "goal_type": "lose",
                        "target_rate_kg_per_week": "0.4",
                        "standard_breakfast_kcal": "330",
                    }
                },
            )
            profile_after_activity = client.get(f"/api/persons/{person_id}/energy-profile")
    finally:
        app.dependency_overrides.clear()

    assert updated.status_code == 200
    assert profile_after_weight.status_code == 200
    assert profile_after_weight.json()["weight_kg"] == "101.5000"
    assert profile_after_weight.json()["activity_level"] == "light"
    assert profile_after_weight.json()["goal_type"] == "lose"
    assert profile_after_weight.json()["standard_breakfast_kcal"] == "330.00"

    assert activity_update.status_code == 200
    assert profile_after_activity.status_code == 200
    assert profile_after_activity.json()["weight_kg"] == "101.5000"
    assert profile_after_activity.json()["activity_level"] == "moderate"

    assert discovery.status_code == 200
    assert discovery.json()["inherits_family_defaults"] is False
    assert discovery.json()["meal_discovery_sources"] == ["shared_recipes"]
    assert discovery.json()["restaurant_area"] == "Benfica"

    person_uuid = uuid.UUID(person_id)
    assert db_session.scalar(
        select(func.count())
        .select_from(AnthropometricMeasurement)
        .where(AnthropometricMeasurement.person_id == person_uuid)
    ) == 3
    assert db_session.scalar(
        select(func.count())
        .select_from(AnthropometricMeasurement)
        .where(
            AnthropometricMeasurement.person_id == person_uuid,
            AnthropometricMeasurement.metric == "height",
        )
    ) == 1
    assert db_session.scalar(
        select(func.count())
        .select_from(AnthropometricMeasurement)
        .where(
            AnthropometricMeasurement.person_id == person_uuid,
            AnthropometricMeasurement.metric == "weight",
        )
    ) == 2
    assert db_session.scalar(
        select(func.count())
        .select_from(NutritionGoal)
        .where(NutritionGoal.person_id == person_uuid)
    ) == 3
    assert db_session.scalar(
        select(func.count())
        .select_from(NutritionTarget)
        .where(NutritionTarget.person_id == person_uuid)
    ) == 3
    assert db_session.scalar(
        select(func.count())
        .select_from(NutritionTarget)
        .where(
            NutritionTarget.person_id == person_uuid,
            NutritionTarget.status == "active",
        )
    ) == 1


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
