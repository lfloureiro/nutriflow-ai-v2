import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.food_catalog import FoodItem, Recipe, RecipeIngredient
from app.models.recipe_variant import FamilyRecipeVariant
from app.schemas.recipe_variant import (
    VariantParticipantValidation,
    VariantRead,
    VariantValidationRead,
)
from app.services.dietary_review import require_family, require_person
from app.services.meal_plan_fit import _load_daily_state, _load_person
from app.services.meal_plan_fit_weekly_frequency import apply_weekly_frequency_to_loaded_fit
from app.services.meal_recommendation import _food_subjects, build_recipe_candidate
from app.services.meal_transformation import _evaluate_loaded_candidate
from app.services.planning_restrictions import automatic_excluded_foods
from app.services.recipe_nutrition import build_recipe_composition
from app.services.recipe_variant_integrity import load_recipe, recipe_fingerprint, variant_issues


def get_variant(db, family_id, variant_id, *, lock=False):
    require_family(db, family_id)
    query = select(FamilyRecipeVariant).where(
        FamilyRecipeVariant.id == variant_id, FamilyRecipeVariant.family_id == family_id
    )
    row = db.scalar(
        query.with_for_update().execution_options(populate_existing=True) if lock else query
    )
    if row is None:
        raise HTTPException(404, "Recipe variant not found in this Family")
    return row


def read_variant(db, row):
    recipe = load_recipe(db, row.recipe_id)
    base = load_recipe(db, row.base_recipe_id)
    energy = recipe.compositions[-1].energy_kcal if recipe.compositions else None
    return VariantRead(
        id=row.id,
        base_recipe_id=row.base_recipe_id,
        recipe_id=row.recipe_id,
        base_name=base.name,
        name=row.name,
        revision=row.revision,
        version=row.version,
        status=row.status,
        serving_count=recipe.serving_count,
        operations=row.operations,
        issues=variant_issues(db, row),
        energy_per_serving=energy / recipe.serving_count
        if energy is not None and recipe.serving_count
        else None,
    )


def list_variants(db, family_id, base_recipe_id=None):
    require_family(db, family_id)
    query = select(FamilyRecipeVariant).where(FamilyRecipeVariant.family_id == family_id)
    if base_recipe_id:
        query = query.where(FamilyRecipeVariant.base_recipe_id == base_recipe_id)
    return [
        read_variant(db, r)
        for r in db.scalars(query.order_by(FamilyRecipeVariant.created_at.desc()))
    ]


def create_variant(db, family_id, data):
    require_family(db, family_id)
    base = load_recipe(db, data.base_recipe_id)
    if base is None or base.family_id not in (None, family_id) or not base.is_active:
        raise HTTPException(404, "Base recipe not available in this Family")
    if base.source == "family_variant" or not base.ingredients:
        raise HTTPException(422, "Choose an original recipe with identified ingredients")
    lineage = uuid.uuid4()
    revision = 1
    if data.revises_variant_id:
        previous = get_variant(db, family_id, data.revises_variant_id)
        if previous.base_recipe_id != base.id:
            raise HTTPException(422, "A revision must keep the same base recipe")
        lineage = previous.lineage_id
        revision = previous.revision + 1
    by_id = {i.id: i for i in base.ingredients}
    operations = {o.recipe_ingredient_id: o for o in data.operations}
    if not set(operations) <= set(by_id):
        raise HTTPException(422, "An operation does not belong to this base recipe")
    replacements = {}
    for o in data.operations:
        food = db.get(FoodItem, o.replacement_food_item_id)
        if food is None or food.family_id not in (None, family_id) or not food.is_active:
            raise HTTPException(404, "Replacement ingredient unavailable in this Family")
        if food.id == by_id[o.recipe_ingredient_id].food_item_id:
            raise HTTPException(422, "Replacement must identify a different food")
        replacements[food.id] = food
    recipe = Recipe(
        family_id=family_id,
        recipe_key=f"variant:{uuid.uuid4()}",
        name=f"{base.name[:55]} · {data.name}"[:160],
        description=base.description,
        suitable_meal_types=base.suitable_meal_types,
        serving_count=data.serving_count,
        source="family_variant",
        source_reference=str(base.id),
        is_active=False,
    )
    db.add(recipe)
    evidence = []
    for i in base.ingredients:
        if i.food_item.family_id not in (None, family_id) or not i.food_item.is_active:
            raise HTTPException(422, "A base ingredient is unavailable in this Family")
        op = operations.get(i.id)
        food = replacements[op.replacement_food_item_id] if op else i.food_item
        recipe.ingredients.append(
            RecipeIngredient(
                food_item=food,
                quantity=op.quantity if op else i.quantity,
                unit=op.unit if op else i.unit,
                preparation=op.preparation if op else i.preparation,
                sort_order=i.sort_order,
            )
        )
        if op:
            evidence.append(
                {
                    **op.model_dump(mode="json"),
                    "source_food_item_id": str(i.food_item_id),
                    "source_name": i.food_item.name,
                    "source_quantity": str(i.quantity),
                    "source_unit": i.unit,
                    "replacement_name": food.name,
                }
            )
    db.flush()
    build_recipe_composition(recipe)
    db.flush()
    row = FamilyRecipeVariant(
        family_id=family_id,
        base_recipe_id=base.id,
        recipe_id=recipe.id,
        lineage_id=lineage,
        revision=revision,
        name=data.name,
        operations=evidence,
        base_fingerprint=recipe_fingerprint(base),
        variant_fingerprint=recipe_fingerprint(recipe),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "This revision already exists; reload") from exc
    return read_variant(db, row)


def validate_variant(db, family_id, variant_id, data):
    row = get_variant(db, family_id, variant_id)
    if row.version != data.expected_version:
        raise HTTPException(409, "Variant changed; reload")
    for participant in data.participants:
        require_person(db, family_id, participant.person_id)
    issues = variant_issues(db, row)
    recipe = load_recipe(db, row.recipe_id)
    if row.status == "retired":
        issues.append("variant_retired")
    if recipe.suitable_meal_types and data.meal_type not in recipe.suitable_meal_types:
        issues.append("meal_type_not_suitable")
    participants = []
    for p in data.participants:
        fit = None
        blockers = []
        if not issues:
            candidate = build_recipe_candidate(
                recipe.compositions[-1], quantity=p.quantity, quantity_unit="serving"
            )
            person = _load_person(db, p.person_id)
            state = _load_daily_state(
                db, person_id=p.person_id, planning_date=data.planning_date, state_id=None
            )
            fit = _evaluate_loaded_candidate(
                db,
                person=person,
                candidate=candidate,
                planning_date=data.planning_date,
                meal_type=data.meal_type,
                daily_state=state,
            )
            fit = apply_weekly_frequency_to_loaded_fit(
                db,
                person=person,
                candidate=candidate,
                planning_date=data.planning_date,
                meal_type=data.meal_type,
                base_fit=fit,
            )
            excluded = automatic_excluded_foods(
                db, family_id, [p.person_id], data.planning_date, data.meal_type
            )
            for food in excluded:
                if _food_subjects(food) & candidate.subjects:
                    blockers.append(f"active_restriction:{food.name}")
            if not fit.eligible:
                blockers.extend(fit.safety_issues)
                blockers.append(f"plan_fit:{fit.status}")
        participants.append(
            VariantParticipantValidation(
                person_id=p.person_id, eligible=not (issues or blockers), issues=blockers, fit=fit
            )
        )
    return VariantValidationRead(
        variant_id=row.id,
        eligible=not issues and all(p.eligible for p in participants),
        issues=issues,
        participants=participants,
    )


def activate_variant(db, family_id, variant_id, data):
    row = get_variant(db, family_id, variant_id)
    # Serialize revisions of the same base, including concurrent activations.
    db.scalar(select(Recipe).where(Recipe.id == row.base_recipe_id).with_for_update())
    row = get_variant(db, family_id, variant_id, lock=True)
    if row.status != "draft":
        raise HTTPException(409, "Only a draft can be activated; create a new revision")
    result = validate_variant(db, family_id, variant_id, data)
    if not result.eligible:
        raise HTTPException(
            422,
            {
                "message": "Variant not eligible for all selected participants",
                "validation": result.model_dump(mode="json"),
            },
        )
    for previous in db.scalars(
        select(FamilyRecipeVariant).where(
            FamilyRecipeVariant.lineage_id == row.lineage_id,
            FamilyRecipeVariant.status == "active",
            FamilyRecipeVariant.id != row.id,
        )
    ):
        previous.status = "retired"
        previous.version += 1
        db.get(Recipe, previous.recipe_id).is_active = False
    row.status = "active"
    row.version += 1
    row.activation_evidence = {
        "planning_date": str(data.planning_date),
        "meal_type": data.meal_type,
        "participants": data.model_dump(mode="json")["participants"],
        "validation": result.model_dump(mode="json"),
    }
    db.get(Recipe, row.recipe_id).is_active = True
    db.commit()
    return read_variant(db, row)


def retire_variant(db, family_id, variant_id, data):
    row = get_variant(db, family_id, variant_id, lock=True)
    if row.version != data.expected_version:
        raise HTTPException(409, "Variant changed; reload")
    row.status = "retired"
    row.version += 1
    db.get(Recipe, row.recipe_id).is_active = False
    db.commit()
    return read_variant(db, row)
