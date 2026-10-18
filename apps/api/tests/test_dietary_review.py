import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.fodmap_guidance_seed import import_public_guidance
from app.main import app
from app.models import Family, FoodItem, NutritionConstraint, Person, Recipe, RecipeIngredient
from app.models.dietary_review import (
    FodmapReference,
    PersonHealthConditionEvent,
    RecipeSubstitutionReview,
)


@pytest.fixture
def client(db_session: Session):
    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as value:
            yield value
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def household(db_session: Session):
    family = Family(name="Condition tests")
    other = Family(name="Other family")
    db_session.add_all([family, other])
    db_session.flush()
    person = Person(family_id=family.id, first_name="Person")
    second = Person(family_id=family.id, first_name="Second")
    outsider = Person(family_id=other.id, first_name="Outsider")
    db_session.add_all([person, second, outsider])
    db_session.flush()
    return family, other, person, second, outsider


def test_condition_revision_history_and_no_implicit_restrictions(client, db_session, household):
    family, _, person, _, _ = household
    path = f"/api/families/{family.id}/persons/{person.id}/conditions"
    payload = {"code": "SIBO", "name": "SIBO", "notes": "Reported by family"}
    response = client.post(path, json=payload)
    assert response.status_code == 201
    original = response.json()
    assert original["code"] == "sibo"
    assert original["status"] == "reported"
    assert original["started_on"] is None
    assert original["version"] == 1
    assert client.post(path, json=payload).status_code == 409
    assert db_session.scalar(select(func.count()).select_from(NutritionConstraint)) == 0

    url = path + "/" + original["id"]
    changed = client.put(url, json={**payload, "status": "resolved", "expected_version": 1})
    assert changed.status_code == 200
    assert changed.json()["version"] == 2
    assert client.put(url, json={**payload, "expected_version": 1}).status_code == 409
    history = client.get(url + "/history").json()
    assert [r["version"] for r in history] == [2, 1]
    assert history[0]["snapshot"]["status"] == "resolved"
    assert history[1]["snapshot"]["status"] == "reported"
    assert (
        client.put(url, json={**payload, "code": "other", "expected_version": 2}).status_code == 422
    )
    assert db_session.scalar(select(func.count()).select_from(PersonHealthConditionEvent)) == 2


def test_conditions_do_not_leak_between_people_or_families(client, household):
    family, other, person, second, outsider = household
    path = f"/api/families/{family.id}/persons/{person.id}/conditions"
    condition = client.post(path, json={"code": "sibo", "name": "SIBO"}).json()
    assert client.get(f"/api/families/{family.id}/persons/{second.id}/conditions").json() == []
    assert client.get(f"/api/families/{other.id}/persons/{person.id}/conditions").status_code == 404
    assert (
        client.post(
            f"/api/families/{family.id}/persons/{outsider.id}/conditions",
            json={"code": "sibo", "name": "SIBO"},
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/families/{family.id}/persons/{second.id}/conditions/{condition['id']}/history"
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"name": " "},
        {"code": "invalid code"},
        {"status": "confirmed"},
        {"source": "doctor"},
        {"source": "document", "source_reference": " "},
        {"started_on": "2026-10-18", "ended_on": "2026-10-17"},
    ],
)
def test_condition_invalid_input_is_rejected(client, household, changes):
    family, _, person, _, _ = household
    path = f"/api/families/{family.id}/persons/{person.id}/conditions"
    assert client.post(path, json={"code": "sibo", "name": "SIBO", **changes}).status_code == 422


def _catalogue(db, family):
    garlic = FoodItem(catalog_key="legacy-v1:ingredient:4", name="Alho")
    onion = FoodItem(catalog_key="legacy-v1:ingredient:30", name="Cebolas")
    recipe = Recipe(recipe_key="test:two-aromatics", name="Two aromatics", family_id=family.id)
    db.add_all([garlic, onion, recipe])
    db.flush()
    ingredients = [
        RecipeIngredient(
            recipe_id=recipe.id, food_item_id=f.id, quantity=10, unit="g", sort_order=n
        )
        for n, f in enumerate([garlic, onion])
    ]
    db.add_all(ingredients)
    db.flush()
    return recipe, ingredients


def test_public_import_is_idempotent_review_only_and_family_scoped(client, db_session, household):
    family, other, _, _, _ = household
    recipe, ingredients = _catalogue(db_session, family)
    result = import_public_guidance(db_session, family.id)
    assert result == {"new_references": 22, "new_proposals": 2}
    assert import_public_guidance(db_session, family.id) == {
        "new_references": 0,
        "new_proposals": 0,
    }
    path = f"/api/families/{family.id}/recipe-adaptations"
    reviews = client.get(path).json()
    assert len(reviews) == 1
    assert reviews[0]["assessment_status"] == "not_evaluated"
    assert len(reviews[0]["ingredients"]) == 2
    assert all(
        i["substitutions"][0]["replacement_quantity"] is None for i in reviews[0]["ingredients"]
    )
    assert client.get(f"/api/families/{other.id}/recipe-adaptations").json() == []
    refs = client.get(f"/api/families/{family.id}/fodmap-references").json()
    assert len(refs) == 22
    assert all(r["evidence_kind"] == "public_educational_summary" for r in refs)
    assert all(r["source_name"] == "Monash University" for r in refs)
    assert db_session.scalar(select(func.count()).select_from(NutritionConstraint)) == 0
    assert [db_session.get(RecipeIngredient, i.id).quantity for i in ingredients] == [10, 10]
    assert db_session.get(Recipe, recipe.id).name == "Two aromatics"
    assert db_session.scalar(select(func.count()).select_from(FodmapReference)) == 22


def test_substitution_review_concurrency_and_no_recipe_writes(client, db_session, household):
    family, other, _, _, _ = household
    _, ingredients = _catalogue(db_session, family)
    path = f"/api/families/{family.id}/recipe-adaptations"
    payload = {
        "recipe_ingredient_id": str(ingredients[0].id),
        "replacement_name": "Garlic-infused oil",
        "notes": "Review amount",
    }
    result = client.post(path, json=payload)
    assert result.status_code == 201
    row = result.json()
    url = path + "/" + row["id"]
    assert (
        client.post(f"/api/families/{other.id}/recipe-adaptations", json=payload).status_code == 404
    )
    assert (
        client.put(
            f"/api/families/{other.id}/recipe-adaptations/{row['id']}",
            json={
                "expected_version": 1,
                "status": "reviewed",
                "notes": "No",
            },
        ).status_code
        == 404
    )
    change = {"expected_version": 1, "status": "reviewed", "notes": "Still needs a dose"}
    saved = client.put(url, json=change)
    assert saved.status_code == 200
    assert saved.json()["version"] == 2
    assert client.put(url, json=change).status_code == 409
    assert db_session.get(RecipeIngredient, ingredients[0].id).quantity == 10
    assert db_session.get(RecipeSubstitutionReview, uuid.UUID(row["id"])).status == "reviewed"
    for extra in [
        {"replacement_quantity": "10"},
        {"replacement_name": " "},
        {"replacement_quantity": "-1", "replacement_unit": "g"},
    ]:
        assert client.post(path, json={**payload, **extra}).status_code == 422
    assert client.post(path, json={**payload, "reference_id": str(uuid.uuid4())}).status_code == 404


def test_import_preserves_reviewed_proposal_notes(db_session, household):
    family, _, _, _, _ = household
    _catalogue(db_session, family)
    import_public_guidance(db_session, family.id)
    row = db_session.scalars(select(RecipeSubstitutionReview)).first()
    row.status = "reviewed"
    row.notes = "Personal review must survive a re-import"
    db_session.commit()
    import_public_guidance(db_session, family.id)
    db_session.refresh(row)
    assert row.notes == "Personal review must survive a re-import"
    assert row.status == "reviewed"


def test_existing_substitution_quantity_can_be_edited_preserved_and_cleared(
    client, db_session, household
):
    family, _, _, _, _ = household
    _, ingredients = _catalogue(db_session, family)
    path = f"/api/families/{family.id}/recipe-adaptations"
    row = client.post(
        path,
        json={
            "recipe_ingredient_id": str(ingredients[0].id),
            "replacement_name": "Infused oil",
            "replacement_quantity": "20",
            "replacement_unit": "ml",
            "notes": "Whole recipe",
        },
    ).json()
    url = path + "/" + row["id"]
    update = {
        "expected_version": 1,
        "status": "reviewed",
        "notes": "Preparation reviewed",
        "replacement_quantity": "12.5000",
        "replacement_unit": "ml",
    }
    saved = client.put(url, json=update)
    assert saved.status_code == 200
    assert saved.json()["replacement_quantity"] == "12.5000"
    assert saved.json()["replacement_unit"] == "ml"
    assert client.put(url, json=update).status_code == 409
    notes_only = client.put(
        url, json={"expected_version": 2, "status": "proposed", "notes": "Keep amount"}
    )
    assert notes_only.json()["replacement_quantity"] == "12.5000"
    assert notes_only.json()["replacement_unit"] == "ml"
    cleared = client.put(
        url,
        json={
            "expected_version": 3,
            "status": "proposed",
            "notes": "Dose unknown",
            "replacement_quantity": None,
            "replacement_unit": None,
        },
    )
    assert cleared.status_code == 200
    assert cleared.json()["replacement_quantity"] is None
    assert cleared.json()["replacement_unit"] is None
    persisted = client.get(path).json()[0]["ingredients"][0]["substitutions"][0]
    assert persisted["replacement_quantity"] is None and persisted["version"] == 4
    assert db_session.get(RecipeIngredient, ingredients[0].id).quantity == 10


@pytest.mark.parametrize(
    "fields",
    [
        {"replacement_quantity": "5"},
        {"replacement_unit": "ml"},
        {"replacement_quantity": None},
        {"replacement_unit": None},
        {"replacement_quantity": "0", "replacement_unit": "g"},
        {"replacement_quantity": "-1", "replacement_unit": "g"},
        {"replacement_quantity": "2", "replacement_unit": None},
        {"replacement_quantity": None, "replacement_unit": "ml"},
        {"replacement_quantity": "2", "replacement_unit": "kg"},
    ],
)
def test_substitution_quantity_update_rejects_incomplete_or_invalid_pairs(
    client, db_session, household, fields
):
    family, _, _, _, _ = household
    _, ingredients = _catalogue(db_session, family)
    path = f"/api/families/{family.id}/recipe-adaptations"
    row = client.post(
        path, json={"recipe_ingredient_id": str(ingredients[0].id), "replacement_name": "Oil"}
    ).json()
    result = client.put(
        path + "/" + row["id"],
        json={"expected_version": 1, "status": "proposed", "notes": "", **fields},
    )
    assert result.status_code == 422
    persisted = db_session.get(RecipeSubstitutionReview, uuid.UUID(row["id"]))
    assert persisted.version == 1 and persisted.replacement_quantity is None
