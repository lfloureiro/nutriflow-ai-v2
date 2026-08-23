from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.family import Family
from app.models.food_catalog import Recipe
from app.models.person import Person


def _override_db(db_session: Session):
    def override_get_db():
        yield db_session

    return override_get_db


def _base(db_session: Session):
    family = Family(name="Ratings Family", timezone="Europe/Lisbon")
    ana = Person(
        family=family,
        first_name="Ana",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    bruno = Person(
        family=family,
        first_name="Bruno",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    recipe = Recipe(
        family=family,
        recipe_key="family:ratings:recipe:pasta",
        name="Pasta",
        source="user",
    )
    db_session.add_all([family, recipe])
    db_session.flush()
    return family, ana, bruno, recipe


def test_recipe_ratings_are_person_specific_and_aggregated(db_session: Session) -> None:
    family, ana, bruno, recipe = _base(db_session)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            ana_response = client.put(
                f"/api/families/{family.id}/recipes/{recipe.id}/preferences/{ana.id}",
                json={"rating": 5, "notes": "Favorita"},
            )
            assert ana_response.status_code == 200
            assert ana_response.json()["average_rating"] == "5.00"

            bruno_response = client.put(
                f"/api/families/{family.id}/recipes/{recipe.id}/preferences/{bruno.id}",
                json={"rating": 3},
            )
            assert bruno_response.status_code == 200
            body = bruno_response.json()
            assert body["average_rating"] == "4.00"
            assert body["rating_count"] == 2
            assert {item["rating"] for item in body["ratings"]} == {3, 5}

            update_response = client.put(
                f"/api/families/{family.id}/recipes/{recipe.id}/preferences/{ana.id}",
                json={"rating": 1},
            )
            assert update_response.status_code == 200
            assert update_response.json()["average_rating"] == "2.00"
            assert update_response.json()["rating_count"] == 2

            clear_response = client.delete(
                f"/api/families/{family.id}/recipes/{recipe.id}/preferences/{bruno.id}"
            )
            assert clear_response.status_code == 200
            assert clear_response.json()["average_rating"] == "1.00"
            assert clear_response.json()["rating_count"] == 1
    finally:
        app.dependency_overrides.clear()


def test_recipe_rating_rejects_person_from_another_family(db_session: Session) -> None:
    family, _, _, recipe = _base(db_session)
    other_family = Family(name="Other", timezone="Europe/Lisbon")
    outsider = Person(
        family=other_family,
        first_name="Outside",
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )
    db_session.add(other_family)
    db_session.flush()
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            response = client.put(
                f"/api/families/{family.id}/recipes/{recipe.id}/preferences/{outsider.id}",
                json={"rating": 5},
            )
            assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_recipe_rating_validates_zero_to_five(db_session: Session) -> None:
    family, ana, _, recipe = _base(db_session)
    app.dependency_overrides[get_db] = _override_db(db_session)
    try:
        with TestClient(app) as client:
            zero_response = client.put(
                f"/api/families/{family.id}/recipes/{recipe.id}/preferences/{ana.id}",
                json={"rating": 0},
            )
            assert zero_response.status_code == 200
            assert zero_response.json()["average_rating"] == "0.00"

            invalid_response = client.put(
                f"/api/families/{family.id}/recipes/{recipe.id}/preferences/{ana.id}",
                json={"rating": 6},
            )
            assert invalid_response.status_code == 422
    finally:
        app.dependency_overrides.clear()
