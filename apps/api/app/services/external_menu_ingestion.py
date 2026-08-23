import hashlib
import json
from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem, FoodNutrientComponent
from app.models.meal_candidate_availability import (
    MealCandidateAvailability,
    MealCommercialOffer,
)
from app.schemas.external_menu import (
    ExternalMenuItemIngestedRead,
    ExternalMenuItemObservationWrite,
)


def _digest(*parts: str, length: int = 32) -> str:
    raw = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:length]


def _catalog_key(data: ExternalMenuItemObservationWrite) -> str:
    digest = _digest(data.provider_key, data.merchant_key, data.item_key)
    return f"external:{data.provider_key[:24]}:{digest}"


def _source_key(data: ExternalMenuItemObservationWrite) -> str:
    digest = _digest(data.provider_key, data.merchant_key, length=24)
    return f"external:{data.provider_key[:24]}:{digest}"


def _offer_key(data: ExternalMenuItemObservationWrite) -> str:
    digest = _digest(
        data.provider_key,
        data.merchant_key,
        data.item_key,
        length=48,
    )
    return f"external:{data.provider_key[:24]}:{digest}"


def _nutrition_version(data: ExternalMenuItemObservationWrite) -> str:
    nutrition = data.nutrition
    if nutrition is None:
        raise ValueError("Nutrition is required to build a composition version.")
    payload = {
        "energy_kcal": str(nutrition.energy_kcal),
        "evidence_level": nutrition.evidence_level,
        "confidence": None if nutrition.confidence is None else str(nutrition.confidence),
        "reference_quantity": str(nutrition.reference_quantity),
        "reference_unit": nutrition.reference_unit,
        "nutrients": [
            {"key": item.key, "value": str(item.value), "unit": item.unit}
            for item in nutrition.nutrients
        ],
        "source_reference": data.source_reference,
        "observed_at": data.observed_at.isoformat(),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"external-menu-{_digest(serialized, length=40)}"


def ingest_external_menu_item(
    db: Session,
    *,
    family: Family,
    data: ExternalMenuItemObservationWrite,
) -> ExternalMenuItemIngestedRead:
    catalog_key = _catalog_key(data)
    food_item = db.scalar(select(FoodItem).where(FoodItem.catalog_key == catalog_key))
    if food_item is None:
        food_item = FoodItem(
            family_id=None,
            catalog_key=catalog_key,
            name=data.item_name,
            food_kind="dish",
            brand=data.merchant_name,
            description=data.description,
            source=data.provider_key[:32],
            source_reference=data.source_reference,
            is_active=True,
        )
        db.add(food_item)
        db.flush()
    else:
        food_item.name = data.item_name
        food_item.brand = data.merchant_name
        food_item.description = data.description
        food_item.source_reference = data.source_reference
        food_item.is_active = True

    composition: FoodCompositionSnapshot | None = None
    observed_at = data.observed_at.astimezone(UTC)
    valid_until = None if data.valid_until is None else data.valid_until.astimezone(UTC)
    if data.nutrition is not None:
        data_version = _nutrition_version(data)
        composition = db.scalar(
            select(FoodCompositionSnapshot).where(
                FoodCompositionSnapshot.food_item_id == food_item.id,
                FoodCompositionSnapshot.data_version == data_version,
            )
        )
        if composition is None:
            note = {
                "evidence_level": data.nutrition.evidence_level,
                "confidence": (
                    None
                    if data.nutrition.confidence is None
                    else str(data.nutrition.confidence)
                ),
                "provider_key": data.provider_key,
                "merchant_key": data.merchant_key,
                "item_key": data.item_key,
            }
            composition = FoodCompositionSnapshot(
                food_item_id=food_item.id,
                reference_quantity=data.nutrition.reference_quantity,
                reference_unit=data.nutrition.reference_unit,
                energy_kcal=data.nutrition.energy_kcal,
                data_version=data_version,
                source=data.provider_key[:32],
                source_reference=data.source_reference,
                effective_at=observed_at,
                notes=json.dumps(note, sort_keys=True),
            )
            db.add(composition)
            db.flush()
            for nutrient in data.nutrition.nutrients:
                db.add(
                    FoodNutrientComponent(
                        composition_snapshot_id=composition.id,
                        nutrient_key=nutrient.key,
                        value=nutrient.value,
                        unit=nutrient.unit,
                    )
                )

    source_key = _source_key(data)
    availability = db.scalar(
        select(MealCandidateAvailability).where(
            MealCandidateAvailability.family_id == family.id,
            MealCandidateAvailability.food_item_id == food_item.id,
            MealCandidateAvailability.source_kind == data.source_kind,
            MealCandidateAvailability.source_key == source_key,
        )
    )
    if availability is None:
        availability = MealCandidateAvailability(
            family_id=family.id,
            food_item_id=food_item.id,
            recipe_id=None,
            candidate_kind="food_item",
            source_kind=data.source_kind,
            source_key=source_key,
            location=data.location,
            preparation_minutes=None,
            requires_kitchen=False,
            is_available=True,
            source=data.provider_key[:32],
            source_reference=data.source_reference,
            notes=f"External menu item from {data.merchant_name}.",
        )
        db.add(availability)
        db.flush()
    else:
        availability.location = data.location
        availability.is_available = True
        availability.source_reference = data.source_reference

    offer_key = _offer_key(data)
    offer = db.scalar(
        select(MealCommercialOffer).where(
            MealCommercialOffer.family_id == family.id,
            MealCommercialOffer.offer_key == offer_key,
        )
    )
    if offer is None:
        offer = MealCommercialOffer(
            family_id=family.id,
            availability_id=availability.id,
            offer_key=offer_key,
            provider_key=data.provider_key,
            provider_name=data.provider_name,
            item_price=data.item_price,
            currency=data.currency.upper(),
            delivery_fee=data.delivery_fee,
            minimum_order=data.minimum_order,
            is_available=True,
            valid_from=observed_at,
            valid_until=valid_until,
            observed_at=observed_at,
            source=data.provider_key[:32],
            source_reference=data.source_reference,
            notes=f"Observed external menu offer for {data.item_name}.",
        )
        db.add(offer)
        db.flush()
    else:
        offer.availability_id = availability.id
        offer.provider_name = data.provider_name
        offer.item_price = data.item_price
        offer.currency = data.currency.upper()
        offer.delivery_fee = data.delivery_fee
        offer.minimum_order = data.minimum_order
        offer.is_available = True
        offer.valid_from = observed_at
        offer.valid_until = valid_until
        offer.observed_at = observed_at
        offer.source_reference = data.source_reference

    db.flush()
    return ExternalMenuItemIngestedRead(
        food_item_id=food_item.id,
        catalog_key=food_item.catalog_key,
        availability_id=availability.id,
        offer_id=offer.id,
        composition_id=None if composition is None else composition.id,
        eligible_for_nutrition_ranking=composition is not None,
    )
