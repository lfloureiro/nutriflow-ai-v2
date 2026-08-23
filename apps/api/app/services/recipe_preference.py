import uuid
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.food_catalog import Recipe
from app.models.food_preference import FoodPreference
from app.models.person import Person
from app.schemas.recipe_preference import (
    PersonRecipeRatingRead,
    RecipePreferenceSummaryRead,
    RecipeRatingWrite,
)
from app.services.recipe_preference_scoring import effective_family_rating

RATING_QUANTUM = Decimal("0.01")


class RecipePreferenceError(ValueError):
    pass


class RecipePreferenceNotFoundError(RecipePreferenceError):
    pass


def _recipe(db: Session, family_id: uuid.UUID, recipe_id: uuid.UUID) -> Recipe:
    recipe = db.scalar(
        select(Recipe).where(
            Recipe.id == recipe_id,
            or_(
                Recipe.family_id == family_id,
                and_(Recipe.family_id.is_(None), Recipe.is_active.is_(True)),
            ),
        )
    )
    if recipe is None:
        raise RecipePreferenceNotFoundError("Recipe not found")
    return recipe


def _person(db: Session, family_id: uuid.UUID, person_id: uuid.UUID) -> Person:
    person = db.scalar(
        select(Person).where(Person.id == person_id, Person.family_id == family_id)
    )
    if person is None:
        raise RecipePreferenceNotFoundError("Person not found")
    return person


def _rating_preferences(
    db: Session,
    *,
    person_id: uuid.UUID,
    recipe_key: str,
) -> list[FoodPreference]:
    return list(
        db.scalars(
            select(FoodPreference)
            .where(
                FoodPreference.person_id == person_id,
                FoodPreference.subject_type == "recipe",
                FoodPreference.subject_key == recipe_key,
                FoodPreference.preference_type == "rating",
            )
            .order_by(FoodPreference.updated_at.desc(), FoodPreference.created_at.desc())
        ).all()
    )


def set_recipe_rating(
    db: Session,
    *,
    family_id: uuid.UUID,
    recipe_id: uuid.UUID,
    person_id: uuid.UUID,
    data: RecipeRatingWrite,
) -> RecipePreferenceSummaryRead:
    recipe = _recipe(db, family_id, recipe_id)
    person = _person(db, family_id, person_id)
    existing = _rating_preferences(db, person_id=person.id, recipe_key=recipe.recipe_key)
    if existing:
        rating = existing[0]
        rating.intensity = data.rating
        rating.notes = data.notes
        rating.source = "user"
        rating.start_date = None
        rating.end_date = None
        for duplicate in existing[1:]:
            db.delete(duplicate)
    else:
        db.add(
            FoodPreference(
                person=person,
                subject_type="recipe",
                subject_key=recipe.recipe_key,
                preference_type="rating",
                intensity=data.rating,
                source="user",
                notes=data.notes,
            )
        )
    db.commit()
    return get_recipe_preference_summary(db, family_id=family_id, recipe_id=recipe_id)


def clear_recipe_rating(
    db: Session,
    *,
    family_id: uuid.UUID,
    recipe_id: uuid.UUID,
    person_id: uuid.UUID,
) -> RecipePreferenceSummaryRead:
    recipe = _recipe(db, family_id, recipe_id)
    _person(db, family_id, person_id)
    for rating in _rating_preferences(db, person_id=person_id, recipe_key=recipe.recipe_key):
        db.delete(rating)
    db.commit()
    return get_recipe_preference_summary(db, family_id=family_id, recipe_id=recipe_id)


def get_recipe_preference_summary(
    db: Session,
    *,
    family_id: uuid.UUID,
    recipe_id: uuid.UUID,
) -> RecipePreferenceSummaryRead:
    recipe = _recipe(db, family_id, recipe_id)
    rows = db.execute(
        select(FoodPreference, Person)
        .join(Person, Person.id == FoodPreference.person_id)
        .where(
            Person.family_id == family_id,
            FoodPreference.subject_type == "recipe",
            FoodPreference.subject_key == recipe.recipe_key,
            FoodPreference.preference_type == "rating",
        )
        .order_by(Person.first_name, Person.last_name, Person.id)
    ).all()
    latest_by_person: dict[uuid.UUID, tuple[FoodPreference, Person]] = {}
    for preference, person in rows:
        current = latest_by_person.get(person.id)
        if current is None or preference.updated_at > current[0].updated_at:
            latest_by_person[person.id] = (preference, person)

    ratings = [
        PersonRecipeRatingRead(
            person_id=person.id,
            first_name=person.first_name,
            last_name=person.last_name,
            rating=preference.intensity,
            notes=preference.notes,
            updated_at=preference.updated_at,
        )
        for preference, person in latest_by_person.values()
    ]
    average = None
    if ratings:
        average = (
            sum((Decimal(rating.rating) for rating in ratings), start=Decimal(0))
            / Decimal(len(ratings))
        ).quantize(RATING_QUANTUM, rounding=ROUND_HALF_UP)
    return RecipePreferenceSummaryRead(
        recipe_id=recipe.id,
        average_rating=average,
        rating_count=len(ratings),
        ratings=ratings,
    )


def load_family_recipe_ratings(
    db: Session,
    *,
    family_id: uuid.UUID,
    planning_date: date,
    exclude_person_id: uuid.UUID | None = None,
) -> dict[str, Decimal]:
    statement = (
        select(FoodPreference)
        .join(Person, Person.id == FoodPreference.person_id)
        .where(
            Person.family_id == family_id,
            FoodPreference.subject_type == "recipe",
            FoodPreference.preference_type == "rating",
            or_(FoodPreference.start_date.is_(None), FoodPreference.start_date <= planning_date),
            or_(FoodPreference.end_date.is_(None), FoodPreference.end_date >= planning_date),
        )
        .order_by(FoodPreference.subject_key, FoodPreference.person_id, FoodPreference.updated_at.desc())
    )
    if exclude_person_id is not None:
        statement = statement.where(FoodPreference.person_id != exclude_person_id)

    latest: dict[tuple[str, uuid.UUID], FoodPreference] = {}
    for preference in db.scalars(statement).all():
        latest.setdefault((preference.subject_key, preference.person_id), preference)

    grouped: dict[str, list[Decimal]] = defaultdict(list)
    for preference in latest.values():
        grouped[preference.subject_key].append(Decimal(preference.intensity))
    return {
        recipe_key: effective_family_rating(values)
        for recipe_key, values in grouped.items()
    }
