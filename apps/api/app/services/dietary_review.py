import uuid

from fastapi import HTTPException
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.dietary_review import (
    FodmapReference,
    FoodFodmapReference,
    PersonHealthCondition,
    PersonHealthConditionEvent,
    RecipeSubstitutionReview,
)
from app.models.family import Family
from app.models.food_catalog import FoodItem, Recipe, RecipeIngredient
from app.models.person import Person
from app.models.recipe_variant import FamilyRecipeVariant
from app.schemas.dietary_review import (
    ConditionRead,
    ConditionUpdate,
    ConditionWrite,
    FodmapReferenceRead,
    ReviewIngredientRead,
    ReviewRecipeRead,
    SubstitutionRead,
    SubstitutionUpdate,
    SubstitutionWrite,
)
from app.services.recipe_variant_integrity import variant_issues


def require_family(db: Session, family_id: uuid.UUID) -> None:
    if db.get(Family, family_id) is None:
        raise HTTPException(404, "Family not found")


def require_person(db: Session, family_id: uuid.UUID, person_id: uuid.UUID) -> None:
    person = db.get(Person, person_id)
    if person is None or person.family_id != family_id:
        raise HTTPException(404, "Person not found in this Family")


def get_condition(db: Session, family_id: uuid.UUID, person_id: uuid.UUID, condition_id: uuid.UUID):
    require_person(db, family_id, person_id)
    row = db.get(PersonHealthCondition, condition_id)
    if row is None or row.person_id != person_id:
        raise HTTPException(404, "Condition not found for this Person")
    return row


def save_condition(
    db: Session,
    family_id: uuid.UUID,
    person_id: uuid.UUID,
    data: ConditionWrite,
    condition_id: uuid.UUID | None = None,
) -> PersonHealthCondition:
    require_person(db, family_id, person_id)
    values = data.model_dump(exclude={"expected_version"})
    try:
        if condition_id is None:
            row = PersonHealthCondition(person_id=person_id, version=1, **values)
            db.add(row)
            db.flush()
        else:
            row = get_condition(db, family_id, person_id, condition_id)
            assert isinstance(data, ConditionUpdate)
            if values["code"] != row.code:
                raise HTTPException(
                    422, "Condition code is immutable; edit the display name instead"
                )
            changed = db.execute(
                update(PersonHealthCondition)
                .where(
                    PersonHealthCondition.id == row.id,
                    PersonHealthCondition.version == data.expected_version,
                )
                .values(**values, version=data.expected_version + 1)
            )
            if changed.rowcount != 1:
                raise HTTPException(409, "Condition changed; reload before saving")
            db.refresh(row)
        db.add(
            PersonHealthConditionEvent(
                condition_id=row.id,
                version=row.version,
                snapshot=ConditionRead.model_validate(row).model_dump(mode="json"),
            )
        )
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "This condition code already exists for this Person") from exc


def recipe_reviews(db: Session, family_id: uuid.UUID) -> list[ReviewRecipeRead]:
    require_family(db, family_id)
    active_variants = {}
    for v in db.scalars(
        select(FamilyRecipeVariant)
        .where(FamilyRecipeVariant.family_id == family_id, FamilyRecipeVariant.status == "active")
        .order_by(FamilyRecipeVariant.created_at.desc())
    ):
        if not variant_issues(db, v):
            active_variants.setdefault(v.base_recipe_id, []).append(
                {
                    "id": str(v.id),
                    "recipe_id": str(v.recipe_id),
                    "name": v.name,
                    "operations": v.operations,
                }
            )
    recipes = db.scalars(
        select(Recipe)
        .where(
            or_(Recipe.family_id == family_id, Recipe.family_id.is_(None)),
            Recipe.is_active.is_(True),
            Recipe.source != "family_variant",
        )
        .options(selectinload(Recipe.ingredients).selectinload(RecipeIngredient.food_item))
        .order_by(Recipe.name, Recipe.id)
    ).all()
    food_ids = {i.food_item_id for r in recipes for i in r.ingredients}
    references: dict[uuid.UUID, list[FodmapReferenceRead]] = {}
    if food_ids:
        for link, reference in db.execute(
            select(FoodFodmapReference, FodmapReference)
            .join(FodmapReference, FodmapReference.id == FoodFodmapReference.reference_id)
            .where(FoodFodmapReference.food_item_id.in_(food_ids))
            .order_by(FodmapReference.reference_key)
        ):
            references.setdefault(link.food_item_id, []).append(
                FodmapReferenceRead.model_validate(reference),
            )
    substitutions: dict[uuid.UUID, list[SubstitutionRead]] = {}
    for row in db.scalars(
        select(RecipeSubstitutionReview)
        .where(
            RecipeSubstitutionReview.family_id == family_id,
        )
        .order_by(RecipeSubstitutionReview.created_at, RecipeSubstitutionReview.id)
    ):
        substitutions.setdefault(row.recipe_ingredient_id, []).append(
            SubstitutionRead.model_validate(row),
        )
    return [
        ReviewRecipeRead(
            id=r.id,
            name=r.name,
            source=r.source,
            serving_count=r.serving_count,
            active_variants=active_variants.get(r.id, []),
            ingredients=[
                ReviewIngredientRead(
                    id=i.id,
                    food_item_id=i.food_item_id,
                    name=i.food_item.name,
                    quantity=i.quantity,
                    unit=i.unit,
                    references=references.get(i.food_item_id, []),
                    substitutions=substitutions.get(i.id, []),
                )
                for i in r.ingredients
            ],
        )
        for r in recipes
    ]


def create_substitution(db: Session, family_id: uuid.UUID, data: SubstitutionWrite):
    require_family(db, family_id)
    ingredient = db.get(RecipeIngredient, data.recipe_ingredient_id)
    if ingredient is None:
        raise HTTPException(404, "Recipe ingredient not found")
    recipe = db.get(Recipe, ingredient.recipe_id)
    if recipe is None or recipe.family_id not in (None, family_id) or not recipe.is_active:
        raise HTTPException(404, "Recipe not visible in this Family")
    if data.replacement_food_item_id:
        food = db.get(FoodItem, data.replacement_food_item_id)
        if food is None or food.family_id not in (None, family_id) or not food.is_active:
            raise HTTPException(404, "Replacement food not visible in this Family")
    if data.reference_id and db.get(FodmapReference, data.reference_id) is None:
        raise HTTPException(404, "FODMAP reference not found")
    row = RecipeSubstitutionReview(
        family_id=family_id,
        proposal_key=str(uuid.uuid4()),
        **data.model_dump(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def review_substitution(
    db: Session,
    family_id: uuid.UUID,
    proposal_id: uuid.UUID,
    data: SubstitutionUpdate,
):
    require_family(db, family_id)
    row = db.get(RecipeSubstitutionReview, proposal_id)
    if row is None or row.family_id != family_id:
        raise HTTPException(404, "Substitution not found in this Family")
    changed = db.execute(
        update(RecipeSubstitutionReview)
        .where(
            RecipeSubstitutionReview.id == row.id,
            RecipeSubstitutionReview.version == data.expected_version,
        )
        .values(
            **data.model_dump(exclude={"expected_version"}, exclude_unset=True),
            version=data.expected_version + 1,
        )
    )
    if changed.rowcount != 1:
        raise HTTPException(409, "Substitution changed; reload before reviewing")
    db.commit()
    db.refresh(row)
    return row
