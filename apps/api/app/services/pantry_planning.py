import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.food_catalog import FoodItem, Recipe
from app.models.pantry_stock import PantryStockLot
from app.services.meal_recommendation import MealCandidate
from app.services.recommendation_practical_context import CandidatePracticalProfile
from app.services.serving_nutrition import UnsupportedUnitConversionError, convert_quantity

ZERO = Decimal(0)


class PantryPlanningError(ValueError):
    pass


class PantryUnitConversionError(PantryPlanningError):
    pass


@dataclass(frozen=True)
class FoodPantryAssessment:
    food_item_id: uuid.UUID
    catalog_key: str
    name: str
    required_quantity: Decimal
    available_quantity: Decimal
    missing_quantity: Decimal
    unit: str
    stock_lot_ids: tuple[uuid.UUID, ...]

    @property
    def is_sufficient(self) -> bool:
        return self.missing_quantity == ZERO


@dataclass(frozen=True)
class ShoppingRequirement:
    food_item_id: uuid.UUID
    catalog_key: str
    name: str
    quantity: Decimal
    unit: str


@dataclass(frozen=True)
class RecipePantryAssessment:
    recipe_id: uuid.UUID
    recipe_key: str
    batch_multiplier: Decimal
    ingredients: tuple[FoodPantryAssessment, ...]
    shopping_requirements: tuple[ShoppingRequirement, ...]

    @property
    def is_sufficient(self) -> bool:
        return not self.shopping_requirements


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _validate_as_of(as_of: datetime) -> None:
    if not _is_timezone_aware(as_of):
        raise PantryPlanningError("as_of must be timezone-aware.")


def _validate_food_scope(food_item: FoodItem, family_id: uuid.UUID) -> uuid.UUID:
    if food_item.id is None:
        raise PantryPlanningError(
            f"FoodItem {food_item.catalog_key!r} must be persisted before pantry evaluation."
        )
    if food_item.family_id not in {None, family_id}:
        raise PantryPlanningError(
            f"FoodItem {food_item.catalog_key!r} belongs to another Family."
        )
    return food_item.id


def _validate_recipe_scope(recipe: Recipe, family_id: uuid.UUID) -> uuid.UUID:
    if recipe.id is None:
        raise PantryPlanningError(
            f"Recipe {recipe.recipe_key!r} must be persisted before pantry evaluation."
        )
    if recipe.family_id not in {None, family_id}:
        raise PantryPlanningError(f"Recipe {recipe.recipe_key!r} belongs to another Family.")
    return recipe.id


def _active_stock_lots(
    session: Session,
    *,
    family_id: uuid.UUID,
    food_item_id: uuid.UUID,
    as_of: datetime,
) -> list[PantryStockLot]:
    return list(
        session.scalars(
            select(PantryStockLot)
            .where(
                PantryStockLot.family_id == family_id,
                PantryStockLot.food_item_id == food_item_id,
                PantryStockLot.is_available.is_(True),
                or_(PantryStockLot.expires_at.is_(None), PantryStockLot.expires_at > as_of),
            )
            .order_by(PantryStockLot.expires_at, PantryStockLot.stock_key)
        ).all()
    )


def _convert_stock_quantity(
    value: Decimal,
    from_unit: str,
    to_unit: str,
    *,
    catalog_key: str,
) -> Decimal:
    try:
        return convert_quantity(value, from_unit, to_unit)
    except UnsupportedUnitConversionError as exc:
        raise PantryUnitConversionError(
            f"Cannot compare pantry stock for {catalog_key!r}: "
            f"{from_unit!r} and {to_unit!r} are not safely convertible."
        ) from exc


def assess_food_pantry_stock(
    session: Session,
    *,
    family_id: uuid.UUID,
    food_item: FoodItem,
    required_quantity: Decimal,
    required_unit: str,
    as_of: datetime,
) -> FoodPantryAssessment:
    _validate_as_of(as_of)
    if required_quantity <= ZERO:
        raise PantryPlanningError("required_quantity must be positive.")
    if not required_unit:
        raise PantryPlanningError("required_unit must not be empty.")

    food_item_id = _validate_food_scope(food_item, family_id)
    lots = _active_stock_lots(
        session,
        family_id=family_id,
        food_item_id=food_item_id,
        as_of=as_of,
    )
    available = sum(
        (
            _convert_stock_quantity(
                lot.quantity_available,
                lot.unit,
                required_unit,
                catalog_key=food_item.catalog_key,
            )
            for lot in lots
        ),
        start=ZERO,
    )
    missing = max(required_quantity - available, ZERO)
    lot_ids = tuple(lot.id for lot in lots if lot.id is not None)

    return FoodPantryAssessment(
        food_item_id=food_item_id,
        catalog_key=food_item.catalog_key,
        name=food_item.name,
        required_quantity=required_quantity,
        available_quantity=available,
        missing_quantity=missing,
        unit=required_unit,
        stock_lot_ids=lot_ids,
    )


def _aggregate_recipe_requirements(
    recipe: Recipe,
    *,
    family_id: uuid.UUID,
    batch_multiplier: Decimal,
) -> list[tuple[FoodItem, Decimal, str]]:
    grouped: dict[uuid.UUID, tuple[FoodItem, Decimal, str]] = {}
    for ingredient in recipe.ingredients:
        food_item = ingredient.food_item
        food_item_id = _validate_food_scope(food_item, family_id)
        required = ingredient.quantity * batch_multiplier
        existing = grouped.get(food_item_id)
        if existing is None:
            grouped[food_item_id] = (food_item, required, ingredient.unit)
            continue

        existing_food, existing_quantity, existing_unit = existing
        converted = _convert_stock_quantity(
            required,
            ingredient.unit,
            existing_unit,
            catalog_key=food_item.catalog_key,
        )
        grouped[food_item_id] = (
            existing_food,
            existing_quantity + converted,
            existing_unit,
        )

    return sorted(grouped.values(), key=lambda item: item[0].catalog_key)


def evaluate_recipe_pantry_sufficiency(
    session: Session,
    *,
    family_id: uuid.UUID,
    recipe: Recipe,
    as_of: datetime,
    batch_multiplier: Decimal = Decimal(1),
) -> RecipePantryAssessment:
    _validate_as_of(as_of)
    if batch_multiplier <= ZERO:
        raise PantryPlanningError("batch_multiplier must be positive.")

    recipe_id = _validate_recipe_scope(recipe, family_id)
    ingredient_assessments = tuple(
        assess_food_pantry_stock(
            session,
            family_id=family_id,
            food_item=food_item,
            required_quantity=required_quantity,
            required_unit=required_unit,
            as_of=as_of,
        )
        for food_item, required_quantity, required_unit in _aggregate_recipe_requirements(
            recipe,
            family_id=family_id,
            batch_multiplier=batch_multiplier,
        )
    )
    shopping_requirements = tuple(
        ShoppingRequirement(
            food_item_id=assessment.food_item_id,
            catalog_key=assessment.catalog_key,
            name=assessment.name,
            quantity=assessment.missing_quantity,
            unit=assessment.unit,
        )
        for assessment in ingredient_assessments
        if not assessment.is_sufficient
    )

    return RecipePantryAssessment(
        recipe_id=recipe_id,
        recipe_key=recipe.recipe_key,
        batch_multiplier=batch_multiplier,
        ingredients=ingredient_assessments,
        shopping_requirements=shopping_requirements,
    )


def _recipe_candidate_batch_multiplier(candidate: MealCandidate) -> Decimal:
    recipe = candidate.recipe
    if recipe is None:
        raise PantryPlanningError(f"Candidate {candidate.key!r} is not a Recipe candidate.")
    if recipe.yield_quantity is None or recipe.yield_unit is None:
        raise PantryPlanningError(
            f"Recipe {recipe.recipe_key!r} needs yield quantity/unit for pantry candidate scaling."
        )
    try:
        requested_yield = convert_quantity(
            candidate.quantity,
            candidate.quantity_unit,
            recipe.yield_unit,
        )
    except UnsupportedUnitConversionError as exc:
        raise PantryUnitConversionError(
            f"Cannot scale Recipe {recipe.recipe_key!r} from candidate unit "
            f"{candidate.quantity_unit!r} to yield unit {recipe.yield_unit!r}."
        ) from exc
    return requested_yield / recipe.yield_quantity


def build_pantry_stock_practical_profiles(
    session: Session,
    *,
    family_id: uuid.UUID,
    candidates: list[MealCandidate],
    as_of: datetime,
) -> tuple[CandidatePracticalProfile, ...]:
    _validate_as_of(as_of)
    profiles: list[CandidatePracticalProfile] = []
    for candidate in candidates:
        if candidate.food_item is not None:
            assessment = assess_food_pantry_stock(
                session,
                family_id=family_id,
                food_item=candidate.food_item,
                required_quantity=candidate.quantity,
                required_unit=candidate.quantity_unit,
                as_of=as_of,
            )
            is_available = assessment.is_sufficient
        elif candidate.recipe is not None:
            assessment = evaluate_recipe_pantry_sufficiency(
                session,
                family_id=family_id,
                recipe=candidate.recipe,
                as_of=as_of,
                batch_multiplier=_recipe_candidate_batch_multiplier(candidate),
            )
            is_available = assessment.is_sufficient
        else:
            raise PantryPlanningError(
                f"Candidate {candidate.key!r} has no FoodItem or Recipe identity."
            )

        profiles.append(
            CandidatePracticalProfile(
                candidate_key=candidate.key,
                is_available=is_available,
            )
        )
    return tuple(profiles)
