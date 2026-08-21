import uuid
from collections import defaultdict

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.meal_candidate_availability import (
    AVAILABILITY_KINDS,
    MealCandidateAvailability,
)
from app.services.meal_recommendation import MealCandidate
from app.services.recommendation_practical_context import CandidatePracticalProfile


class PersistedPracticalAvailabilityError(ValueError):
    pass


def _candidate_identity(
    candidate: MealCandidate,
    *,
    family_id: uuid.UUID,
) -> tuple[str, uuid.UUID]:
    if candidate.food_item is not None:
        if candidate.food_item.id is None:
            raise PersistedPracticalAvailabilityError(
                f"Food candidate {candidate.key!r} must be persisted before availability lookup."
            )
        if candidate.food_item.family_id not in {None, family_id}:
            raise PersistedPracticalAvailabilityError(
                f"Food candidate {candidate.key!r} belongs to another Family."
            )
        return "food_item", candidate.food_item.id

    if candidate.recipe is not None:
        if candidate.recipe.id is None:
            raise PersistedPracticalAvailabilityError(
                f"Recipe candidate {candidate.key!r} must be persisted before availability lookup."
            )
        if candidate.recipe.family_id not in {None, family_id}:
            raise PersistedPracticalAvailabilityError(
                f"Recipe candidate {candidate.key!r} belongs to another Family."
            )
        return "recipe", candidate.recipe.id

    raise PersistedPracticalAvailabilityError(
        f"Candidate {candidate.key!r} has no persisted FoodItem or Recipe identity."
    )


def _availability_kind_filter(
    availability_kinds: frozenset[str] | None,
) -> frozenset[str] | None:
    if availability_kinds is None:
        return None
    if not availability_kinds:
        raise PersistedPracticalAvailabilityError(
            "availability_kinds must be omitted or contain at least one source kind."
        )
    unsupported = availability_kinds - AVAILABILITY_KINDS
    if unsupported:
        raise PersistedPracticalAvailabilityError(
            "Unsupported availability kinds: " + ", ".join(sorted(unsupported)) + "."
        )
    return availability_kinds


def _profile_from_rows(
    candidate_key: str,
    rows: list[MealCandidateAvailability],
    availability_kinds: frozenset[str] | None,
) -> CandidatePracticalProfile:
    selected = [
        row
        for row in rows
        if availability_kinds is None or row.source_kind in availability_kinds
    ]
    available = [row for row in selected if row.is_available]
    if not available:
        return CandidatePracticalProfile(
            candidate_key=candidate_key,
            is_available=False,
        )

    preparation_minutes = min(
        (
            row.preparation_minutes
            for row in available
            if row.preparation_minutes is not None
        ),
        default=None,
    )
    available_locations: frozenset[str] | None = None
    if all(row.location for row in available):
        available_locations = frozenset(
            row.location for row in available if row.location is not None
        )

    return CandidatePracticalProfile(
        candidate_key=candidate_key,
        is_available=True,
        available_locations=available_locations,
        preparation_minutes=preparation_minutes,
        requires_kitchen=all(row.requires_kitchen for row in available),
    )


def build_persisted_practical_profiles(
    session: Session,
    *,
    family_id: uuid.UUID,
    candidates: list[MealCandidate],
    availability_kinds: frozenset[str] | None = None,
) -> tuple[CandidatePracticalProfile, ...]:
    requested_kinds = _availability_kind_filter(availability_kinds)
    if not candidates:
        return ()

    identities = {
        candidate.key: _candidate_identity(candidate, family_id=family_id)
        for candidate in candidates
    }
    food_ids = [identity for kind, identity in identities.values() if kind == "food_item"]
    recipe_ids = [identity for kind, identity in identities.values() if kind == "recipe"]

    filters = []
    if food_ids:
        filters.append(MealCandidateAvailability.food_item_id.in_(food_ids))
    if recipe_ids:
        filters.append(MealCandidateAvailability.recipe_id.in_(recipe_ids))

    rows = session.scalars(
        select(MealCandidateAvailability).where(
            MealCandidateAvailability.family_id == family_id,
            or_(*filters),
        )
    ).all()
    grouped: dict[tuple[str, uuid.UUID], list[MealCandidateAvailability]] = defaultdict(list)
    for row in rows:
        if row.candidate_kind == "food_item" and row.food_item_id is not None:
            grouped[("food_item", row.food_item_id)].append(row)
        elif row.candidate_kind == "recipe" and row.recipe_id is not None:
            grouped[("recipe", row.recipe_id)].append(row)

    profiles: list[CandidatePracticalProfile] = []
    for candidate in candidates:
        candidate_rows = grouped.get(identities[candidate.key], [])
        if not candidate_rows:
            continue
        profiles.append(
            _profile_from_rows(candidate.key, candidate_rows, requested_kinds)
        )
    return tuple(profiles)
