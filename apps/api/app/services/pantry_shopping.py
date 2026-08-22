import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.family import Family
from app.models.food_catalog import FoodItem, Recipe, RecipeIngredient
from app.models.meal import MealEvent, MealParticipant, Serving
from app.models.pantry_stock import PantryStockLot
from app.models.shopping_list import ShoppingList, ShoppingListItem
from app.schemas.pantry_shopping import (
    PantryLotCreate,
    PantryLotRead,
    PantryLotUpdate,
    PlannedRequirementRead,
    ShoppingListItemCreate,
    ShoppingListItemRead,
    ShoppingListItemUpdate,
    ShoppingListRead,
)
from app.services.pantry_planning import PantryPlanningError, assess_food_pantry_stock
from app.services.serving_nutrition import UnsupportedUnitConversionError, convert_quantity

ZERO = Decimal(0)
PLANNING_STATUSES = frozenset({"planned", "prepared"})


class PantryShoppingError(ValueError):
    pass


class PantryLotNotFoundError(PantryShoppingError):
    pass


class ShoppingListItemNotFoundError(PantryShoppingError):
    pass


@dataclass(frozen=True)
class PlannedRequirementsResult:
    requirements: tuple[PlannedRequirementRead, ...]
    issues: tuple[str, ...]


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _pantry_options():
    return (selectinload(PantryStockLot.food_item),)


def _pantry_read(lot: PantryStockLot) -> PantryLotRead:
    return PantryLotRead(
        id=lot.id,
        family_id=lot.family_id,
        food_item_id=lot.food_item_id,
        food_item_name=lot.food_item.name,
        stock_key=lot.stock_key,
        quantity_available=lot.quantity_available,
        unit=lot.unit,
        location=lot.location,
        expires_at=lot.expires_at,
        observed_at=lot.observed_at,
        is_available=lot.is_available,
        notes=lot.notes,
        created_at=lot.created_at,
        updated_at=lot.updated_at,
    )


def _pantry_food(db: Session, family_id: uuid.UUID, food_item_id: uuid.UUID) -> FoodItem:
    item = db.scalar(
        select(FoodItem).where(
            FoodItem.id == food_item_id,
            FoodItem.is_active.is_(True),
            or_(FoodItem.family_id == family_id, FoodItem.family_id.is_(None)),
        )
    )
    if item is None:
        raise PantryShoppingError("Food item is not available to this Family.")
    return item


def list_pantry_lots(
    db: Session,
    family_id: uuid.UUID,
    *,
    include_inactive: bool = False,
) -> list[PantryLotRead]:
    statement = (
        select(PantryStockLot)
        .options(*_pantry_options())
        .where(PantryStockLot.family_id == family_id)
        .order_by(PantryStockLot.food_item_id, PantryStockLot.expires_at, PantryStockLot.id)
    )
    if not include_inactive:
        statement = statement.where(PantryStockLot.is_available.is_(True))
    return [_pantry_read(lot) for lot in db.scalars(statement).all()]


def _get_pantry_lot(db: Session, family_id: uuid.UUID, lot_id: uuid.UUID) -> PantryStockLot:
    lot = db.scalar(
        select(PantryStockLot)
        .options(*_pantry_options())
        .where(PantryStockLot.id == lot_id, PantryStockLot.family_id == family_id)
    )
    if lot is None:
        raise PantryLotNotFoundError("Pantry stock lot not found")
    return lot


def create_pantry_lot(
    db: Session,
    family: Family,
    data: PantryLotCreate,
) -> PantryLotRead:
    food_item = _pantry_food(db, family.id, data.food_item_id)
    lot = PantryStockLot(
        family=family,
        food_item=food_item,
        stock_key=f"family:{family.id}:pantry:{uuid.uuid4()}",
        quantity_available=data.quantity_available,
        unit=data.unit.lower(),
        location=_optional_text(data.location),
        expires_at=data.expires_at,
        observed_at=datetime.now(UTC),
        is_available=True,
        source="user",
        source_reference="nutriflow-pantry-editor",
        notes=_optional_text(data.notes),
    )
    db.add(lot)
    db.commit()
    return _pantry_read(lot)


def update_pantry_lot(
    db: Session,
    family_id: uuid.UUID,
    lot_id: uuid.UUID,
    data: PantryLotUpdate,
) -> PantryLotRead:
    lot = _get_pantry_lot(db, family_id, lot_id)
    fields = data.model_fields_set
    if "quantity_available" in fields and data.quantity_available is not None:
        lot.quantity_available = data.quantity_available
    if "unit" in fields and data.unit is not None:
        lot.unit = data.unit.lower()
    if "location" in fields:
        lot.location = _optional_text(data.location)
    if "expires_at" in fields:
        lot.expires_at = data.expires_at
    if "is_available" in fields and data.is_available is not None:
        lot.is_available = data.is_available
    if "notes" in fields:
        lot.notes = _optional_text(data.notes)
    lot.observed_at = datetime.now(UTC)
    db.commit()
    return _pantry_read(lot)


def deactivate_pantry_lot(db: Session, family_id: uuid.UUID, lot_id: uuid.UUID) -> None:
    lot = _get_pantry_lot(db, family_id, lot_id)
    lot.is_available = False
    lot.observed_at = datetime.now(UTC)
    db.commit()


def _utc_bounds(family: Family, start_date: date, days: int) -> tuple[datetime, datetime]:
    timezone = ZoneInfo(family.timezone)
    local_start = datetime.combine(start_date, time.min, tzinfo=timezone)
    local_end = datetime.combine(start_date + timedelta(days=days), time.min, tzinfo=timezone)
    return local_start.astimezone(UTC), local_end.astimezone(UTC)


def _serving_options():
    return (
        selectinload(Serving.recipe)
        .selectinload(Recipe.ingredients)
        .selectinload(RecipeIngredient.food_item),
    )


def _batch_multiplier(serving: Serving, recipe: Recipe) -> Decimal:
    quantity = serving.quantity_planned
    unit = serving.quantity_unit
    if quantity is None or unit is None:
        raise PantryShoppingError(f"Serving {serving.id} has no planned quantity evidence.")

    if recipe.yield_quantity is not None and recipe.yield_unit is not None:
        try:
            requested = convert_quantity(quantity, unit, recipe.yield_unit)
        except UnsupportedUnitConversionError as exc:
            raise PantryShoppingError(
                f"Recipe {recipe.name!r} portion cannot be converted from {unit!r} "
                f"to yield unit {recipe.yield_unit!r}."
            ) from exc
        return requested / recipe.yield_quantity

    if recipe.serving_count is not None and unit == "serving":
        return quantity / recipe.serving_count
    if unit == "recipe":
        return quantity
    raise PantryShoppingError(
        f"Recipe {recipe.name!r} needs yield evidence or serving-based portions "
        "for shopping calculation."
    )


def _aggregate_planned_ingredients(
    db: Session,
    family: Family,
    start_date: date,
    days: int,
) -> tuple[dict[uuid.UUID, tuple[FoodItem, Decimal, str]], list[str]]:
    start_at, end_at = _utc_bounds(family, start_date, days)
    servings = db.scalars(
        select(Serving)
        .options(*_serving_options())
        .join(Serving.meal_participant)
        .join(MealParticipant.meal_event)
        .where(
            MealEvent.family_id == family.id,
            MealEvent.scheduled_at >= start_at,
            MealEvent.scheduled_at < end_at,
            MealEvent.status.in_(PLANNING_STATUSES),
            Serving.recipe_id.is_not(None),
            Serving.status == "planned",
        )
    ).all()

    grouped: dict[uuid.UUID, tuple[FoodItem, Decimal, str]] = {}
    invalid_food_ids: set[uuid.UUID] = set()
    issues: list[str] = []
    for serving in servings:
        recipe = serving.recipe
        if recipe is None:
            continue
        try:
            multiplier = _batch_multiplier(serving, recipe)
        except PantryShoppingError as exc:
            issues.append(str(exc))
            continue

        for ingredient in recipe.ingredients:
            food = ingredient.food_item
            if food.id in invalid_food_ids:
                continue
            required = ingredient.quantity * multiplier
            existing = grouped.get(food.id)
            if existing is None:
                grouped[food.id] = (food, required, ingredient.unit)
                continue
            existing_food, existing_quantity, existing_unit = existing
            try:
                converted = convert_quantity(required, ingredient.unit, existing_unit)
            except UnsupportedUnitConversionError:
                issues.append(
                    f"Ingredient {food.name!r} uses incompatible planned units "
                    f"{ingredient.unit!r} and {existing_unit!r}."
                )
                invalid_food_ids.add(food.id)
                grouped.pop(food.id, None)
                continue
            grouped[food.id] = (
                existing_food,
                existing_quantity + converted,
                existing_unit,
            )
    return grouped, issues


def build_planned_requirements(
    db: Session,
    family: Family,
    *,
    start_date: date,
    days: int,
    as_of: datetime | None = None,
) -> PlannedRequirementsResult:
    if not 1 <= days <= 14:
        raise PantryShoppingError("days must be between 1 and 14.")
    grouped, issues = _aggregate_planned_ingredients(db, family, start_date, days)
    instant = as_of or datetime.now(UTC)
    requirements: list[PlannedRequirementRead] = []
    for food, required_quantity, unit in sorted(
        grouped.values(), key=lambda value: value[0].name.lower()
    ):
        try:
            assessment = assess_food_pantry_stock(
                db,
                family_id=family.id,
                food_item=food,
                required_quantity=required_quantity,
                required_unit=unit,
                as_of=instant,
            )
        except PantryPlanningError as exc:
            issues.append(str(exc))
            continue
        requirements.append(
            PlannedRequirementRead(
                food_item_id=assessment.food_item_id,
                food_item_name=assessment.name,
                required_quantity=assessment.required_quantity,
                available_quantity=assessment.available_quantity,
                missing_quantity=assessment.missing_quantity,
                unit=assessment.unit,
            )
        )
    return PlannedRequirementsResult(
        requirements=tuple(requirements),
        issues=tuple(dict.fromkeys(issues)),
    )


def _shopping_options():
    return (selectinload(ShoppingList.items).selectinload(ShoppingListItem.food_item),)


def _active_shopping_list(db: Session, family: Family) -> ShoppingList:
    shopping_list = db.scalar(
        select(ShoppingList)
        .options(*_shopping_options())
        .where(ShoppingList.family_id == family.id, ShoppingList.status == "active")
        .order_by(ShoppingList.created_at.desc())
        .limit(1)
    )
    if shopping_list is not None:
        return shopping_list
    shopping_list = ShoppingList(
        family=family,
        list_key=f"family:{family.id}:shopping:{uuid.uuid4()}",
        title="Compras",
        status="active",
        source="user",
        source_reference="nutriflow-shopping-list",
    )
    db.add(shopping_list)
    db.flush()
    return shopping_list


def _item_read(item: ShoppingListItem) -> ShoppingListItemRead:
    return ShoppingListItemRead(
        id=item.id,
        food_item_id=item.food_item_id,
        name=item.name,
        quantity=item.quantity,
        unit=item.unit,
        item_source=item.item_source,
        status=item.status,
        notes=item.notes,
        sort_order=item.sort_order,
    )


def _shopping_read(
    shopping_list: ShoppingList,
    result: PlannedRequirementsResult,
) -> ShoppingListRead:
    return ShoppingListRead(
        id=shopping_list.id,
        family_id=shopping_list.family_id,
        title=shopping_list.title,
        status=shopping_list.status,
        planning_start=shopping_list.planning_start,
        planning_end=shopping_list.planning_end,
        generated_at=shopping_list.generated_at,
        requirements=list(result.requirements),
        planning_issues=list(result.issues),
        items=[_item_read(item) for item in shopping_list.items],
        created_at=shopping_list.created_at,
        updated_at=shopping_list.updated_at,
    )


def get_shopping_list(db: Session, family: Family) -> ShoppingListRead:
    shopping_list = _active_shopping_list(db, family)
    if shopping_list.planning_start is None or shopping_list.planning_end is None:
        result = PlannedRequirementsResult(requirements=(), issues=())
    else:
        days = (shopping_list.planning_end - shopping_list.planning_start).days + 1
        result = build_planned_requirements(
            db,
            family,
            start_date=shopping_list.planning_start,
            days=days,
        )
    db.commit()
    return _shopping_read(shopping_list, result)


def refresh_shopping_list(
    db: Session,
    family: Family,
    *,
    start_date: date,
    days: int,
) -> ShoppingListRead:
    result = build_planned_requirements(db, family, start_date=start_date, days=days)
    shopping_list = _active_shopping_list(db, family)
    shopping_list.planning_start = start_date
    shopping_list.planning_end = start_date + timedelta(days=days - 1)
    shopping_list.generated_at = datetime.now(UTC)
    shopping_list.source = "planner"
    shopping_list.source_reference = "family-meal-plan"

    automatic = {
        item.food_item_id: item
        for item in shopping_list.items
        if item.item_source == "automatic" and item.food_item_id is not None
    }
    desired = {
        requirement.food_item_id: requirement
        for requirement in result.requirements
        if requirement.missing_quantity > ZERO
    }

    for food_item_id, item in list(automatic.items()):
        if food_item_id not in desired and item.status == "needed":
            shopping_list.items.remove(item)
            db.delete(item)

    for sort_order, requirement in enumerate(desired.values()):
        existing = automatic.get(requirement.food_item_id)
        if existing is not None:
            if existing.status == "needed":
                existing.name = requirement.food_item_name
                existing.quantity = requirement.missing_quantity
                existing.unit = requirement.unit
                existing.sort_order = sort_order
            continue
        shopping_list.items.append(
            ShoppingListItem(
                food_item_id=requirement.food_item_id,
                item_key=f"food:{requirement.food_item_id}",
                name=requirement.food_item_name,
                quantity=requirement.missing_quantity,
                unit=requirement.unit,
                item_source="automatic",
                status="needed",
                sort_order=sort_order,
                source_reference="family-meal-plan",
            )
        )

    db.commit()
    shopping_list = db.scalar(
        select(ShoppingList)
        .options(*_shopping_options())
        .where(ShoppingList.id == shopping_list.id)
    )
    if shopping_list is None:
        raise PantryShoppingError("Shopping list disappeared after refresh.")
    return _shopping_read(shopping_list, result)


def add_manual_shopping_item(
    db: Session,
    family: Family,
    data: ShoppingListItemCreate,
) -> ShoppingListRead:
    shopping_list = _active_shopping_list(db, family)
    manual_count = sum(item.item_source == "manual" for item in shopping_list.items)
    shopping_list.items.append(
        ShoppingListItem(
            item_key=f"manual:{uuid.uuid4()}",
            name=data.name,
            quantity=data.quantity,
            unit=data.unit.lower() if data.unit else None,
            item_source="manual",
            status="needed",
            sort_order=10_000 + manual_count,
            notes=_optional_text(data.notes),
            source_reference="manual",
        )
    )
    db.commit()
    return get_shopping_list(db, family)


def _shopping_item(
    db: Session,
    family_id: uuid.UUID,
    item_id: uuid.UUID,
) -> ShoppingListItem:
    item = db.scalar(
        select(ShoppingListItem)
        .join(ShoppingListItem.shopping_list)
        .where(
            ShoppingListItem.id == item_id,
            ShoppingList.family_id == family_id,
            ShoppingList.status == "active",
        )
    )
    if item is None:
        raise ShoppingListItemNotFoundError("Shopping list item not found")
    return item


def update_shopping_item(
    db: Session,
    family: Family,
    item_id: uuid.UUID,
    data: ShoppingListItemUpdate,
) -> ShoppingListRead:
    item = _shopping_item(db, family.id, item_id)
    fields = data.model_fields_set
    if "name" in fields and data.name is not None:
        item.name = data.name
    if "quantity" in fields:
        item.quantity = data.quantity
        item.unit = data.unit.lower() if data.unit else None
    if "status" in fields and data.status is not None:
        item.status = data.status
    if "notes" in fields:
        item.notes = _optional_text(data.notes)
    db.commit()
    return get_shopping_list(db, family)


def delete_shopping_item(
    db: Session,
    family_id: uuid.UUID,
    item_id: uuid.UUID,
) -> None:
    item = _shopping_item(db, family_id, item_id)
    db.delete(item)
    db.commit()
