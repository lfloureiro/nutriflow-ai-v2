import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.legacy_v1_demo_seed import LEGACY_V1_NAMESPACE
from app.models.family import Family
from app.models.food_catalog import (
    FoodItem,
    Recipe,
    RecipeCompositionSnapshot,
    RecipeIngredient,
)
from app.models.food_preference import FoodPreference
from app.models.person import Person

V1_COMMIT = "88eae17dc622f023021436317ba18486a99ef344"
V1_SNAPSHOT_PATH = "data/dataset_snapshots/20260426_101840Z_backup-actual.json"
V1_SNAPSHOT_BLOB_SHA = "7b62de5235c50021b479a131a6fe7d0dc8784f9a"
V1_SNAPSHOT_URL = (
    "https://raw.githubusercontent.com/lfloureiro/nutriflow-ai/"
    f"{V1_COMMIT}/{V1_SNAPSHOT_PATH}"
)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
V1_CACHE_PATH = (
    PROJECT_ROOT
    / "database"
    / "legacy-v1"
    / "cache"
    / "20260426_101840Z_backup-actual.json"
)
SOURCE = "legacy-v1"
SOURCE_REFERENCE = f"nutriflow-ai@{V1_COMMIT}:{V1_SNAPSHOT_PATH}"
LOUREIRO_NAMESPACE = uuid.UUID("2fe1cd37-2f06-4c62-bc16-2f92b137889b")
LOUREIRO_FAMILY_ID = uuid.uuid5(LOUREIRO_NAMESPACE, "household:1")
LOUREIRO_TIMEZONE = "Europe/Lisbon"
OLD_SYNTHETIC_CALCULATION_VERSION = "legacy-v1-demo-synthetic-nutrition-v1"


class LegacyV1LoureiroSeedError(RuntimeError):
    pass


@dataclass(frozen=True)
class LegacyV1LoureiroSeedResult:
    family_id: uuid.UUID
    member_count: int
    ingredient_count: int
    recipe_count: int
    rating_count: int


def _git_blob_sha(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _verified_payload(payload: bytes) -> bytes:
    actual = _git_blob_sha(payload)
    if actual != V1_SNAPSHOT_BLOB_SHA:
        raise LegacyV1LoureiroSeedError(
            "NutriFlow v1 snapshot content did not match the pinned Git blob SHA."
        )
    return payload


def _load_snapshot_bytes() -> bytes:
    if V1_CACHE_PATH.exists():
        cached = V1_CACHE_PATH.read_bytes()
        if _git_blob_sha(cached) == V1_SNAPSHOT_BLOB_SHA:
            return cached

    request = Request(
        V1_SNAPSHOT_URL,
        headers={"User-Agent": "NutriFlowAI-v2-development-import"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = _verified_payload(response.read())
    except (HTTPError, URLError, TimeoutError) as exc:
        raise LegacyV1LoureiroSeedError(
            "Could not download the pinned NutriFlow v1 Loureiro snapshot. "
            "Connect to the Internet once so the development seed can cache it locally."
        ) from exc

    V1_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    V1_CACHE_PATH.write_bytes(payload)
    return payload


def load_loureiro_snapshot() -> dict[str, object]:
    try:
        payload = json.loads(_load_snapshot_bytes().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LegacyV1LoureiroSeedError("The pinned v1 snapshot is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise LegacyV1LoureiroSeedError("The pinned v1 snapshot has an invalid root shape.")
    return payload


def _data(snapshot: dict[str, object]) -> dict[str, object]:
    value = snapshot.get("data")
    if not isinstance(value, dict):
        raise LegacyV1LoureiroSeedError("The v1 snapshot is missing its data object.")
    return value


def _rows(data: dict[str, object], key: str) -> list[dict[str, object]]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise LegacyV1LoureiroSeedError(f"The v1 snapshot has invalid {key!r} data.")
    return value


def _legacy_catalog_id(kind: str, legacy_id: int) -> uuid.UUID:
    return uuid.uuid5(LEGACY_V1_NAMESPACE, f"{kind}:{legacy_id}")


def _person_id(legacy_id: int) -> uuid.UUID:
    return uuid.uuid5(LOUREIRO_NAMESPACE, f"family-member:{legacy_id}")


def _rating_id(legacy_id: int) -> uuid.UUID:
    return uuid.uuid5(LOUREIRO_NAMESPACE, f"recipe-preference:{legacy_id}")


def _as_int(value: object, *, field: str) -> int:
    if isinstance(value, bool):
        raise LegacyV1LoureiroSeedError(f"Invalid boolean value for {field}.")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise LegacyV1LoureiroSeedError(f"Invalid integer value for {field}.") from exc


def _text(value: object) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def _quantity_and_unit(row: dict[str, object]) -> tuple[Decimal, str, str | None]:
    raw_quantity = row.get("quantity")
    raw_unit = _text(row.get("unit"))
    if raw_quantity is None:
        return (
            Decimal(1),
            raw_unit or "qb",
            "Quantidade não especificada na v1; importada como 1 qb.",
        )
    try:
        quantity = Decimal(str(raw_quantity))
    except InvalidOperation as exc:
        raise LegacyV1LoureiroSeedError(
            "Invalid recipe ingredient quantity in v1 snapshot."
        ) from exc
    if quantity <= 0:
        return (
            Decimal(1),
            raw_unit or "qb",
            "Quantidade não positiva na v1; importada como 1 qb.",
        )
    return quantity, (raw_unit or "un").lower(), None


def _legacy_timestamp(value: object) -> datetime | None:
    text = _text(value)
    if text is None:
        return None
    instant = datetime.fromisoformat(text)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=ZoneInfo(LOUREIRO_TIMEZONE))
    return instant


def _ensure_family(session: Session) -> Family:
    family = session.get(Family, LOUREIRO_FAMILY_ID)
    if family is None:
        family = Family(
            id=LOUREIRO_FAMILY_ID,
            name="Família Loureiro",
            timezone=LOUREIRO_TIMEZONE,
            meal_discovery_sources=["shared_recipes"],
        )
        session.add(family)
    else:
        family.name = "Família Loureiro"
        family.timezone = LOUREIRO_TIMEZONE
        if not family.meal_discovery_sources:
            family.meal_discovery_sources = ["shared_recipes"]
    return family


def _ensure_people(
    session: Session,
    family: Family,
    rows: list[dict[str, object]],
) -> dict[int, Person]:
    people: dict[int, Person] = {}
    for row in rows:
        if _as_int(row.get("household_id"), field="family member household id") != 1:
            continue
        legacy_id = _as_int(row.get("id"), field="family member id")
        name = _text(row.get("name"))
        if name is None:
            raise LegacyV1LoureiroSeedError("A v1 family member is missing a name.")
        person = session.get(Person, _person_id(legacy_id))
        if person is None:
            person = Person(
                id=_person_id(legacy_id),
                family=family,
                first_name=name,
                last_name=None,
                preferred_locale="pt-PT",
                timezone=LOUREIRO_TIMEZONE,
            )
            session.add(person)
        else:
            person.family_id = family.id
            person.first_name = name
            person.last_name = None
            person.preferred_locale = "pt-PT"
            person.timezone = LOUREIRO_TIMEZONE
        people[legacy_id] = person
    session.flush()
    return people


def _used_ingredient_ids(recipe_ingredient_rows: list[dict[str, object]]) -> set[int]:
    return {
        _as_int(row.get("ingredient_id"), field="recipe ingredient ingredient id")
        for row in recipe_ingredient_rows
    }


def _ensure_ingredients(
    session: Session,
    rows: list[dict[str, object]],
    *,
    used_ids: set[int],
) -> dict[int, FoodItem]:
    ingredients: dict[int, FoodItem] = {}
    for row in rows:
        legacy_id = _as_int(row.get("id"), field="ingredient id")
        if legacy_id not in used_ids:
            continue
        name = _text(row.get("name"))
        if name is None:
            raise LegacyV1LoureiroSeedError("A v1 ingredient is missing a name.")
        item_id = _legacy_catalog_id("ingredient", legacy_id)
        catalog_key = f"legacy-v1:ingredient:{legacy_id}"
        owner = session.scalar(select(FoodItem).where(FoodItem.catalog_key == catalog_key))
        if owner is not None and owner.id != item_id:
            raise LegacyV1LoureiroSeedError(f"Catalogue key conflict for {catalog_key!r}.")
        item = session.get(FoodItem, item_id)
        if item is None:
            item = FoodItem(id=item_id)
            session.add(item)
        item.family_id = None
        item.catalog_key = catalog_key
        item.name = name
        item.food_kind = "ingredient"
        item.source = SOURCE
        item.source_reference = SOURCE_REFERENCE
        item.is_active = True
        ingredients[legacy_id] = item
    missing = used_ids.difference(ingredients)
    if missing:
        raise LegacyV1LoureiroSeedError(
            f"The v1 snapshot is missing recipe ingredients: {sorted(missing)!r}."
        )
    session.flush()
    return ingredients


def _ensure_recipes(
    session: Session,
    rows: list[dict[str, object]],
) -> dict[int, Recipe]:
    recipes: dict[int, Recipe] = {}
    for row in rows:
        legacy_id = _as_int(row.get("id"), field="recipe id")
        name = _text(row.get("name"))
        if name is None:
            raise LegacyV1LoureiroSeedError("A v1 recipe is missing a name.")
        recipe_id = _legacy_catalog_id("recipe", legacy_id)
        recipe_key = f"legacy-v1:recipe:{legacy_id}"
        owner = session.scalar(select(Recipe).where(Recipe.recipe_key == recipe_key))
        if owner is not None and owner.id != recipe_id:
            raise LegacyV1LoureiroSeedError(f"Recipe key conflict for {recipe_key!r}.")
        recipe = session.get(Recipe, recipe_id)
        if recipe is None:
            recipe = Recipe(id=recipe_id)
            session.add(recipe)
        recipe.family_id = None
        recipe.recipe_key = recipe_key
        recipe.name = name
        recipe.description = _text(row.get("description"))
        recipe.yield_quantity = None
        recipe.yield_unit = None
        recipe.serving_count = None
        recipe.source = SOURCE
        recipe.source_reference = SOURCE_REFERENCE
        recipe.is_active = True
        recipes[legacy_id] = recipe
    session.flush()
    return recipes


def _replace_recipe_ingredients(
    session: Session,
    rows: list[dict[str, object]],
    *,
    recipes: dict[int, Recipe],
    ingredients: dict[int, FoodItem],
) -> None:
    recipe_ids = [recipe.id for recipe in recipes.values()]
    if recipe_ids:
        session.execute(
            delete(RecipeIngredient).where(RecipeIngredient.recipe_id.in_(recipe_ids))
        )
        session.execute(
            delete(RecipeCompositionSnapshot).where(
                RecipeCompositionSnapshot.recipe_id.in_(recipe_ids),
                RecipeCompositionSnapshot.calculation_version
                == OLD_SYNTHETIC_CALCULATION_VERSION,
            )
        )
        session.flush()

    sort_orders: dict[int, int] = {}
    for row in rows:
        legacy_row_id = _as_int(row.get("id"), field="recipe ingredient id")
        recipe_legacy_id = _as_int(
            row.get("recipe_id"), field="recipe ingredient recipe id"
        )
        ingredient_legacy_id = _as_int(
            row.get("ingredient_id"),
            field="recipe ingredient ingredient id",
        )
        recipe = recipes.get(recipe_legacy_id)
        ingredient = ingredients.get(ingredient_legacy_id)
        if recipe is None:
            continue
        if ingredient is None:
            raise LegacyV1LoureiroSeedError(
                f"Recipe {recipe_legacy_id} references missing ingredient {ingredient_legacy_id}."
            )
        quantity, unit, note = _quantity_and_unit(row)
        sort_order = sort_orders.get(recipe_legacy_id, 0)
        sort_orders[recipe_legacy_id] = sort_order + 1
        session.add(
            RecipeIngredient(
                id=uuid.uuid5(
                    LOUREIRO_NAMESPACE,
                    f"recipe-ingredient:{legacy_row_id}",
                ),
                recipe_id=recipe.id,
                food_item_id=ingredient.id,
                quantity=quantity,
                unit=unit,
                preparation=None,
                sort_order=sort_order,
                notes=note or "Importado do snapshot real NutriFlow v1.",
            )
        )
    session.flush()


def _ensure_ratings(
    session: Session,
    rows: list[dict[str, object]],
    *,
    people: dict[int, Person],
    recipes: dict[int, Recipe],
) -> int:
    count = 0
    for row in rows:
        household_id = _as_int(row.get("household_id"), field="rating household id")
        if household_id != 1:
            continue
        legacy_id = _as_int(row.get("id"), field="rating id")
        member_id = _as_int(row.get("family_member_id"), field="rating member id")
        recipe_id = _as_int(row.get("recipe_id"), field="rating recipe id")
        rating_value = _as_int(row.get("rating"), field="rating value")
        if rating_value < 0 or rating_value > 5:
            raise LegacyV1LoureiroSeedError("A v1 recipe rating is outside the 0-5 scale.")
        person = people.get(member_id)
        recipe = recipes.get(recipe_id)
        if person is None or recipe is None:
            continue
        preference = session.get(FoodPreference, _rating_id(legacy_id))
        if preference is None:
            preference = FoodPreference(id=_rating_id(legacy_id), person=person)
            session.add(preference)
        preference.person_id = person.id
        preference.subject_type = "recipe"
        preference.subject_key = recipe.recipe_key
        preference.preference_type = "rating"
        preference.intensity = rating_value
        preference.source = SOURCE
        preference.start_date = None
        preference.end_date = None
        preference.notes = _text(row.get("note"))
        source_updated_at = _legacy_timestamp(row.get("updated_at"))
        if source_updated_at is not None:
            preference.updated_at = source_updated_at
        count += 1
    session.flush()
    return count


def seed_loureiro_v1_snapshot(
    session: Session,
    *,
    snapshot: dict[str, object] | None = None,
) -> LegacyV1LoureiroSeedResult:
    source = snapshot or load_loureiro_snapshot()
    data = _data(source)
    households = _rows(data, "households")
    if not any(
        _as_int(row.get("id"), field="household id") == 1
        and _text(row.get("name")) == "Família Loureiro"
        for row in households
    ):
        raise LegacyV1LoureiroSeedError(
            "The pinned v1 snapshot does not contain Família Loureiro."
        )

    family = _ensure_family(session)
    people = _ensure_people(session, family, _rows(data, "family_members"))
    recipe_ingredient_rows = _rows(data, "recipe_ingredients")
    ingredients = _ensure_ingredients(
        session,
        _rows(data, "ingredients"),
        used_ids=_used_ingredient_ids(recipe_ingredient_rows),
    )
    recipes = _ensure_recipes(session, _rows(data, "recipes"))
    _replace_recipe_ingredients(
        session,
        recipe_ingredient_rows,
        recipes=recipes,
        ingredients=ingredients,
    )
    rating_count = _ensure_ratings(
        session,
        _rows(data, "recipe_preferences"),
        people=people,
        recipes=recipes,
    )

    return LegacyV1LoureiroSeedResult(
        family_id=family.id,
        member_count=len(people),
        ingredient_count=len(ingredients),
        recipe_count=len(recipes),
        rating_count=rating_count,
    )
