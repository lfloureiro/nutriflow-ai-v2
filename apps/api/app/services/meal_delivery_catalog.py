import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import cast

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.family import Family
from app.models.food_catalog import FoodCompositionSnapshot, FoodItem
from app.models.meal_candidate_availability import (
    MealCandidateAvailability,
    MealCommercialOffer,
)
from app.schemas.external_menu import NutritionEvidenceLevel
from app.schemas.meal_delivery_sync import MealDeliveryMenuItemRead

_EVIDENCE_LEVELS = frozenset({"official", "provider", "estimated"})


def _latest_composition(
    food_item: FoodItem,
    *,
    observed_at: datetime,
) -> FoodCompositionSnapshot | None:
    eligible = [
        snapshot
        for snapshot in food_item.compositions
        if snapshot.effective_at <= observed_at
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda snapshot: snapshot.effective_at)


def _nutrition_metadata(
    composition: FoodCompositionSnapshot | None,
) -> tuple[NutritionEvidenceLevel | None, Decimal | None]:
    if composition is None or not composition.notes:
        return None, None
    try:
        payload = json.loads(composition.notes)
    except json.JSONDecodeError:
        return None, None
    if not isinstance(payload, dict):
        return None, None

    raw_level = payload.get("evidence_level")
    level = raw_level if isinstance(raw_level, str) and raw_level in _EVIDENCE_LEVELS else None

    raw_confidence = payload.get("confidence")
    confidence: Decimal | None = None
    if raw_confidence is not None:
        try:
            confidence = Decimal(str(raw_confidence))
        except (InvalidOperation, TypeError, ValueError):
            confidence = None

    return cast(NutritionEvidenceLevel | None, level), confidence


def list_meal_delivery_menu_items(
    db: Session,
    *,
    family: Family,
    provider_key: str,
    limit: int = 100,
) -> list[MealDeliveryMenuItemRead]:
    now = datetime.now(UTC)
    offers = db.scalars(
        select(MealCommercialOffer)
        .join(MealCandidateAvailability)
        .where(
            MealCommercialOffer.family_id == family.id,
            MealCommercialOffer.provider_key == provider_key,
            MealCommercialOffer.is_available.is_(True),
            MealCandidateAvailability.is_available.is_(True),
            MealCandidateAvailability.food_item_id.is_not(None),
            or_(MealCommercialOffer.valid_from.is_(None), MealCommercialOffer.valid_from <= now),
            or_(MealCommercialOffer.valid_until.is_(None), MealCommercialOffer.valid_until > now),
        )
        .options(
            selectinload(MealCommercialOffer.availability)
            .selectinload(MealCandidateAvailability.food_item)
            .selectinload(FoodItem.compositions)
        )
        .order_by(
            MealCommercialOffer.observed_at.desc(),
            MealCommercialOffer.created_at.desc(),
        )
        .limit(limit)
    ).all()

    result: list[MealDeliveryMenuItemRead] = []
    for offer in offers:
        availability = offer.availability
        food_item = availability.food_item
        if food_item is None or food_item.family_id != family.id:
            continue
        composition = _latest_composition(food_item, observed_at=offer.observed_at)
        evidence_level, confidence = _nutrition_metadata(composition)
        result.append(
            MealDeliveryMenuItemRead(
                catalog_key=food_item.catalog_key,
                merchant_name=food_item.brand or offer.provider_name or provider_key,
                item_name=food_item.name,
                description=food_item.description,
                item_price=offer.item_price,
                currency=offer.currency,
                delivery_fee=offer.delivery_fee,
                minimum_order=offer.minimum_order,
                source_reference=(
                    offer.source_reference or food_item.source_reference or ""
                ),
                observed_at=offer.observed_at,
                energy_kcal=None if composition is None else composition.energy_kcal,
                nutrition_evidence_level=evidence_level,
                nutrition_confidence=confidence,
                eligible_for_nutrition_ranking=(
                    composition is not None and composition.energy_kcal is not None
                ),
            )
        )
    return result
