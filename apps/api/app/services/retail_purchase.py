import hashlib
import json
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy import select

from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem, FoodNutrientComponent
from app.models.planning_workspace import RetailAlternative
from app.models.retail_confirmation import RetailIngredientConfirmation
from app.services.dietary_review import require_family
from app.services.serving_nutrition import UnsupportedUnitConversionError, convert_quantity


def _number(value):
    return format(Decimal(str(value)).normalize(), "f")


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def label_fingerprint(product):
    return _hash(
        {
            "key": product.product_key,
            "name": product.name,
            "url": product.product_url,
            "ingredients": product.ingredient_summary,
            "nutrition": product.nutrition_per_100,
            "pack": _number(product.pack_quantity),
            "unit": product.pack_unit,
            "evidence": product.evidence_level,
        }
    )


def food_fingerprint(food):
    composition = food.compositions[-1] if food.compositions else None
    return _hash(
        {
            "name": food.name,
            "brand": food.brand,
            "catalog_key": food.catalog_key,
            "source": food.source,
            "description": food.description,
            "active": food.is_active,
            "composition": str(composition.id) if composition else None,
            "basis": [_number(composition.reference_quantity), composition.reference_unit]
            if composition
            else None,
            "energy": _number(composition.energy_kcal)
            if composition and composition.energy_kcal is not None
            else None,
            "nutrients": sorted(
                (n.nutrient_key, _number(n.value), n.unit) for n in composition.nutrients
            )
            if composition
            else [],
        }
    )


def confirmation_issue(product):
    nutrition = product.nutrition_per_100 or {}
    if not product.ingredient_summary.strip():
        return "complete_label_required"
    if product.evidence_level != "retailer_ingredients_and_nutrition":
        return "complete_label_required"
    if nutrition.get("reference_unit") not in ("g", "ml"):
        return "unsupported_nutrition_basis"
    try:
        numbers = [
            Decimal(str(nutrition[key]))
            for key in ("energy_kcal", "protein_g", "carbohydrate_g", "fat_g")
        ]
        if any(not value.is_finite() or value < 0 for value in numbers) or not any(numbers):
            return "invalid_nutrition"
        for key in ("fiber_g", "salt_g"):
            if key in nutrition:
                value = Decimal(str(nutrition[key]))
                if not value.is_finite() or value < 0:
                    return "invalid_nutrition"
    except (KeyError, InvalidOperation, TypeError, ValueError):
        return "complete_label_required"
    return None


def confirmation_current(row):
    return (
        row.food_item.family_id == row.family_id
        and row.label_fingerprint == label_fingerprint(row.retail_product)
        and row.food_fingerprint == food_fingerprint(row.food_item)
        and row.food_item.is_active
        and not confirmation_issue(row.retail_product)
    )


def confirm_ingredient(db, family_id, product_id, data):
    require_family(db, family_id)
    # Serialize duplicate confirmations for this family, without modifying existing foods.
    db.scalar(select(Family).where(Family.id == family_id).with_for_update())
    product = db.scalar(
        select(RetailAlternative).where(RetailAlternative.id == product_id).with_for_update()
    )
    if product is None:
        raise HTTPException(404, "Retail product not found")
    fingerprint = label_fingerprint(product)
    if data.expected_fingerprint != fingerprint:
        raise HTTPException(409, "Product label changed; reload and review again")
    if confirmation_issue(product):
        raise HTTPException(422, "Complete usable ingredients and nutrition are required")
    previous = db.scalar(
        select(RetailIngredientConfirmation).where(
            RetailIngredientConfirmation.family_id == family_id,
            RetailIngredientConfirmation.retail_product_id == product_id,
            RetailIngredientConfirmation.label_fingerprint == fingerprint,
        )
    )
    if previous:
        if not confirmation_current(previous):
            raise HTTPException(
                409, "Confirmed ingredient changed; review its evidence before reuse"
            )
        db.commit()
        return {"food_item_id": previous.food_item_id, "confirmation_id": previous.id}
    nutrition = product.nutrition_per_100
    food = FoodItem(
        family_id=family_id,
        catalog_key=f"retail:{family_id}:{product_id}:{fingerprint[:16]}",
        name=product.name[:160],
        food_kind="ingredient",
        source="retail_review",
        source_reference=str(product.id),
        description=product.ingredient_summary,
    )
    composition = FoodCompositionSnapshot(
        reference_quantity=100,
        reference_unit=nutrition["reference_unit"],
        energy_kcal=Decimal(str(nutrition["energy_kcal"])),
        data_version=f"retail:{fingerprint[:32]}",
        source="retail_review",
        source_reference=product.product_url[:255],
        effective_at=datetime.now(UTC),
        notes="User-reviewed retail label; missing nutrients remain unknown. Not FODMAP certification.",
    )
    for source, key in (
        ("protein_g", "protein"),
        ("carbohydrate_g", "carbohydrate"),
        ("fat_g", "fat"),
        ("fiber_g", "fiber"),
        ("salt_g", "salt"),
    ):
        if source in nutrition:
            composition.nutrients.append(
                FoodNutrientComponent(
                    nutrient_key=key, value=Decimal(str(nutrition[source])), unit="g"
                )
            )
    food.compositions.append(composition)
    db.add(food)
    db.flush()
    row = RetailIngredientConfirmation(
        family_id=family_id,
        retail_product_id=product.id,
        food_item_id=food.id,
        label_fingerprint=fingerprint,
        food_fingerprint=food_fingerprint(food),
        evidence={
            "url": product.product_url,
            "observed_on": str(product.observed_on),
            "ingredients": product.ingredient_summary,
            "nutrition": nutrition,
            "label_reviewed": True,
        },
    )
    db.add(row)
    db.commit()
    return {"food_item_id": food.id, "confirmation_id": row.id}


def package_amounts(quantity, unit, product):
    try:
        needed = convert_quantity(quantity, unit, product.pack_unit)
    except UnsupportedUnitConversionError as exc:
        raise HTTPException(
            422, "Package and ingredient units are incompatible; no density or unit size is assumed"
        ) from exc
    count = int((needed / product.pack_quantity).to_integral_value(rounding=ROUND_CEILING))
    total = product.pack_quantity * count
    return {
        "package_count": count,
        "total_quantity": str(total),
        "excess_quantity": str(total - needed),
        "pack_unit": product.pack_unit,
        "estimated_total": str(product.observed_price * count)
        if product.observed_price is not None
        else None,
    }


def requirement_matches(item, requirement):
    if requirement is None or item.quantity is None or item.unit is None:
        return False
    needed = (
        requirement.to_buy_quantity
        if requirement.to_buy_quantity is not None
        else requirement.missing_quantity
    )
    try:
        return convert_quantity(item.quantity, item.unit, requirement.unit) == needed
    except UnsupportedUnitConversionError:
        return False


def retail_recipe_issues(db, recipe):
    food_ids = [
        ingredient.food_item_id
        for ingredient in recipe.ingredients
        if ingredient.food_item.source == "retail_review"
        or ingredient.food_item.catalog_key.startswith("retail:")
    ]
    if not food_ids:
        return []
    rows = db.scalars(
        select(RetailIngredientConfirmation).where(
            RetailIngredientConfirmation.food_item_id.in_(food_ids)
        )
    ).all()
    return (
        ["retail_label_changed: review ingredient and recipe evidence"]
        if any(not confirmation_current(row) for row in rows)
        else []
    )


def selection_read(item, requirement=None):
    if not item.product_selection:
        return None
    snapshot = dict(item.product_selection)
    issues = []
    if item.status != "purchased":
        row = item.product_confirmation
        if row is None or not confirmation_current(row) or row.food_item_id != item.food_item_id:
            issues.append("label_or_ingredient_changed")
        if (
            item.quantity != Decimal(snapshot["required_quantity"])
            or item.unit != snapshot["required_unit"]
        ):
            issues.append("quantity_changed")
        if item.item_source == "automatic" and not requirement_matches(item, requirement):
            issues.append("shopping_needs_refresh")
    snapshot["status"] = "needs_review" if issues else "confirmed"
    snapshot["issues"] = issues
    if issues:
        for key in ("package_count", "total_quantity", "excess_quantity", "estimated_total"):
            snapshot[key] = None
    return snapshot


def select_product(db, family, item_id, data, *, preview=False):
    from app.services.pantry_shopping import (
        _active_shopping_list,
        _shopping_item,
        get_shopping_list,
    )

    shopping_list = _active_shopping_list(db, family)
    item = _shopping_item(db, family.id, item_id)
    if item.version != data.expected_version:
        raise HTTPException(409, "Shopping item changed; reload before selecting a product")
    if item.status != "needed":
        raise HTTPException(409, "Purchased items keep their recorded product")
    if data.retail_product_id is None:
        item.product_confirmation = None
        item.product_selection = None
    else:
        product = db.scalar(
            select(RetailAlternative)
            .where(RetailAlternative.id == data.retail_product_id)
            .with_for_update()
        )
        if product is None:
            raise HTTPException(404, "Retail product not found")
        if data.expected_fingerprint != label_fingerprint(product):
            raise HTTPException(409, "Product label changed; reload")
        row = db.scalar(
            select(RetailIngredientConfirmation).where(
                RetailIngredientConfirmation.family_id == family.id,
                RetailIngredientConfirmation.food_item_id == item.food_item_id,
                RetailIngredientConfirmation.retail_product_id == product.id,
                RetailIngredientConfirmation.label_fingerprint == label_fingerprint(product),
            )
        )
        if row is None or not confirmation_current(row):
            raise HTTPException(
                422,
                "Product must match the exact confirmed ingredient in this shopping item; apply a validated variant first",
            )
        if item.quantity is None or item.unit is None or item.quantity <= 0:
            raise HTTPException(422, "A confirmed ingredient quantity and unit are required")
        if item.item_source == "automatic":
            from app.services.pantry_shopping import (
                build_planned_requirements,
                requirements_with_incoming,
            )

            if shopping_list.planning_start is None or shopping_list.planning_end is None:
                raise HTTPException(
                    409, "Refresh shopping from the plan before selecting a product"
                )
            result = build_planned_requirements(
                db,
                family,
                start_date=shopping_list.planning_start,
                days=(shopping_list.planning_end - shopping_list.planning_start).days + 1,
            )
            requirement = next(
                (
                    r
                    for r in requirements_with_incoming(shopping_list, result)
                    if r.food_item_id == item.food_item_id
                ),
                None,
            )
            if not requirement_matches(item, requirement):
                raise HTTPException(
                    409, "Refresh shopping to use current effective ingredient quantities"
                )
        amounts = package_amounts(item.quantity, item.unit, product)
        snapshot = {
            "retail_product_id": str(product.id),
            "product_name": product.name,
            "retailer": product.retailer,
            "product_url": product.product_url,
            "observed_on": str(product.observed_on),
            "observed_price": str(product.observed_price)
            if product.observed_price is not None
            else None,
            "pack_quantity": str(product.pack_quantity),
            "pack_unit": product.pack_unit,
            "required_quantity": str(item.quantity),
            "required_unit": item.unit,
            **amounts,
        }
    if preview:
        return snapshot
    if data.retail_product_id is not None:
        item.product_confirmation = row
        item.product_selection = snapshot
    item.version += 1
    db.commit()
    return get_shopping_list(db, family)
