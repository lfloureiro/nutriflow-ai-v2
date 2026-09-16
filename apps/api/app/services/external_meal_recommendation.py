import json
import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.food_catalog import FoodCompositionSnapshot, FoodItem
from app.models.meal_candidate_availability import (
    MealCandidateAvailability,
    MealCommercialOffer,
)
from app.schemas.external_meal_recommendation import (
    ExternalMealCandidateEvidenceRead,
    ExternalMealRecommendationCreate,
    ExternalMealRecommendationRead,
)
from app.schemas.external_menu import NutritionEvidenceLevel
from app.schemas.meal_recommendation import MealRecommendationCandidateInput
from app.schemas.practical_recommendation import PracticalMealRecommendationCreate
from app.services.planning_bootstrap_api import get_planning_bootstrap
from app.services.practical_recommendation_plan_fit_api import (
    create_practical_meal_recommendation_with_plan_fit,
)

_EVIDENCE_LEVELS = frozenset({"official", "provider", "estimated"})


class ExternalMealRecommendationError(ValueError):
    pass


def _offer_is_active(offer: MealCommercialOffer, scheduled_at: datetime) -> bool:
    if not offer.is_available:
        return False
    if offer.valid_from is not None and scheduled_at < offer.valid_from:
        return False
    return offer.valid_until is None or scheduled_at < offer.valid_until


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


def _row_matches_delivery_provider(
    row: MealCandidateAvailability,
    *,
    scheduled_at: datetime,
    provider_keys: frozenset[str],
) -> bool:
    active_offers = [
        offer for offer in row.commercial_offers if _offer_is_active(offer, scheduled_at)
    ]
    if not active_offers:
        return False
    if row.source_kind != "delivery" or not provider_keys:
        return True
    return any(offer.provider_key in provider_keys for offer in active_offers)


def _external_rows(
    session: Session,
    *,
    family_id: uuid.UUID,
    data: ExternalMealRecommendationCreate,
) -> list[MealCandidateAvailability]:
    requested_kinds = frozenset(data.source_kinds)
    rows = session.scalars(
        select(MealCandidateAvailability)
        .where(
            MealCandidateAvailability.family_id == family_id,
            MealCandidateAvailability.source_kind.in_(requested_kinds),
            MealCandidateAvailability.food_item_id.is_not(None),
            MealCandidateAvailability.is_available.is_(True),
        )
        .options(
            selectinload(MealCandidateAvailability.food_item),
            selectinload(MealCandidateAvailability.commercial_offers),
        )
        .order_by(
            MealCandidateAvailability.source_kind,
            MealCandidateAvailability.source_key,
            MealCandidateAvailability.id,
        )
    ).all()
    provider_keys = frozenset(data.delivery_provider_keys)
    return [
        row
        for row in rows
        if row.food_item is not None
        and row.food_item.is_active
        and _row_matches_delivery_provider(
            row,
            scheduled_at=data.scheduled_at,
            provider_keys=provider_keys,
        )
    ]


def _composition_map(
    session: Session,
    composition_ids: set[uuid.UUID],
) -> dict[uuid.UUID, FoodCompositionSnapshot]:
    if not composition_ids:
        return {}
    rows = session.scalars(
        select(FoodCompositionSnapshot).where(
            FoodCompositionSnapshot.id.in_(composition_ids)
        )
    ).all()
    return {row.id: row for row in rows if row.id is not None}


def create_external_meal_recommendation(
    session: Session,
    *,
    person_id: uuid.UUID,
    data: ExternalMealRecommendationCreate,
) -> ExternalMealRecommendationRead:
    bootstrap = get_planning_bootstrap(
        session,
        person_id=person_id,
        scheduled_at=data.scheduled_at,
        ensure_state=True,
    )
    state = bootstrap.daily_nutrition_state
    if state is None:
        raise ExternalMealRecommendationError(
            "Daily nutrition state could not be prepared for external recommendation."
        )

    availability_rows = _external_rows(
        session,
        family_id=bootstrap.family_id,
        data=data,
    )
    rows_by_key: dict[str, list[MealCandidateAvailability]] = defaultdict(list)
    for row in availability_rows:
        food_item = row.food_item
        if food_item is not None:
            rows_by_key[food_item.catalog_key].append(row)

    selected_keys = sorted(rows_by_key)[: data.max_candidates]
    planning_candidates = {
        candidate.catalog_key: candidate
        for candidate in bootstrap.candidates
        if candidate.candidate_kind == "food_item"
        and candidate.catalog_key in selected_keys
    }
    composition_ids = {
        candidate.composition_id for candidate in planning_candidates.values()
    }
    compositions = _composition_map(session, composition_ids)

    evidence: list[ExternalMealCandidateEvidenceRead] = []
    candidate_inputs: list[MealRecommendationCandidateInput] = []
    for catalog_key in selected_keys:
        rows = rows_by_key[catalog_key]
        food_item = rows[0].food_item
        if food_item is None:
            continue
        source_kinds = sorted({row.source_kind for row in rows})
        provider_keys = sorted(
            {
                offer.provider_key
                for row in rows
                for offer in row.commercial_offers
                if _offer_is_active(offer, data.scheduled_at)
            }
        )
        candidate = planning_candidates.get(catalog_key)
        reason: str | None = None
        evaluated = False
        composition: FoodCompositionSnapshot | None = None

        if candidate is None:
            reason = "nutrition_composition_missing"
        elif data.meal_type not in candidate.suitable_meal_types:
            reason = "not_suitable_for_meal_type"
            composition = compositions.get(candidate.composition_id)
        else:
            composition = compositions.get(candidate.composition_id)
            if composition is None:
                reason = "nutrition_composition_missing"
            else:
                candidate_inputs.append(
                    MealRecommendationCandidateInput(
                        candidate_kind="food_item",
                        composition_id=candidate.composition_id,
                        quantity=candidate.reference_quantity,
                        quantity_unit=candidate.reference_unit,
                    )
                )
                evaluated = True

        evidence_level, confidence = _nutrition_metadata(composition)
        evidence.append(
            ExternalMealCandidateEvidenceRead(
                catalog_key=catalog_key,
                item_name=food_item.name,
                merchant_name=food_item.brand,
                source_kinds=source_kinds,
                provider_keys=provider_keys,
                source_reference=food_item.source_reference,
                composition_id=None if composition is None else composition.id,
                reference_quantity=(
                    None if composition is None else composition.reference_quantity
                ),
                reference_unit=None if composition is None else composition.reference_unit,
                nutrition_evidence_level=evidence_level,
                nutrition_confidence=confidence,
                evaluated=evaluated,
                reason=reason,
            )
        )

    recommendation = None
    if candidate_inputs:
        practical = PracticalMealRecommendationCreate(
            daily_nutrition_state_id=state.id,
            planning_date=bootstrap.planning_date,
            scheduled_at=data.scheduled_at,
            meal_type=data.meal_type,
            candidates=candidate_inputs,
            location=data.location,
            available_minutes=data.available_minutes,
            has_kitchen=False,
            source_kinds=list(data.source_kinds),
            delivery_provider_keys=data.delivery_provider_keys,
            auto_size_portions=False,
            max_results=data.max_results,
        )
        recommendation = create_practical_meal_recommendation_with_plan_fit(
            session,
            person_id=person_id,
            data=practical,
        )

    return ExternalMealRecommendationRead(
        person_id=person_id,
        planning_date=bootstrap.planning_date,
        scheduled_at=data.scheduled_at,
        meal_type=data.meal_type,
        discovered_count=len(selected_keys),
        evaluated_count=len(candidate_inputs),
        evidence=evidence,
        recommendation=recommendation,
    )
