import uuid
from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.family import Family
from app.models.meal_candidate_availability import (
    MealCandidateAvailability,
    MealCommercialOffer,
)
from app.models.meal_menu_snapshot import MealMenuSnapshot, MealMenuSnapshotItem
from app.schemas.external_menu import (
    ExternalMenuItemIngestedRead,
    ExternalMenuItemObservationWrite,
)


@dataclass(frozen=True)
class WeekdayMenuPattern:
    food_item_id: uuid.UUID
    item_name: str
    weekday: int
    observed_days: int
    sampled_days: int
    frequency: Decimal


def _set_current_menu_availability(
    db: Session,
    *,
    family_id: uuid.UUID,
    provider_key: str,
    source_kind: str,
    observed_availability_ids: set[uuid.UUID],
) -> None:
    """Reconcile current availability for complete snapshots only.

    The source_key on MealCandidateAvailability identifies a provider+merchant source.
    Reading it from the observed rows avoids duplicating the hashing convention used by
    external-menu ingestion.
    """

    if not observed_availability_ids:
        return

    source_keys = set(
        db.scalars(
            select(MealCandidateAvailability.source_key).where(
                MealCandidateAvailability.id.in_(observed_availability_ids)
            )
        ).all()
    )
    for source_key in source_keys:
        availabilities = db.scalars(
            select(MealCandidateAvailability).where(
                MealCandidateAvailability.family_id == family_id,
                MealCandidateAvailability.source_kind == source_kind,
                MealCandidateAvailability.source_key == source_key,
            )
        ).all()
        availability_ids = {availability.id for availability in availabilities}
        for availability in availabilities:
            availability.is_available = availability.id in observed_availability_ids

        if not availability_ids:
            continue
        offers = db.scalars(
            select(MealCommercialOffer).where(
                MealCommercialOffer.availability_id.in_(availability_ids),
                MealCommercialOffer.provider_key == provider_key,
            )
        ).all()
        for offer in offers:
            offer.is_available = offer.availability_id in observed_availability_ids


def record_menu_snapshots(
    db: Session,
    *,
    family: Family,
    provider_key: str,
    observations: tuple[ExternalMenuItemObservationWrite, ...],
    ingested: tuple[ExternalMenuItemIngestedRead, ...],
    query: str | None,
    limit: int,
) -> tuple[MealMenuSnapshot, ...]:
    """Persist dated menu evidence and reconcile today's menu when safely complete.

    A result with fewer rows than the requested limit is treated as complete. If the
    provider returns exactly the limit, positive observations are still stored but
    missing historical dishes are not marked unavailable because the result may have
    been truncated.
    """

    if len(observations) != len(ingested):
        raise ValueError("observations and ingested rows must have the same length.")
    if not observations:
        return ()

    is_complete = len(observations) < limit
    grouped: dict[
        tuple[str, str, str],
        list[tuple[ExternalMenuItemObservationWrite, ExternalMenuItemIngestedRead]],
    ] = defaultdict(list)
    for observation, ingested_item in zip(observations, ingested, strict=True):
        grouped[
            (
                observation.merchant_key,
                observation.merchant_name,
                observation.source_kind,
            )
        ].append((observation, ingested_item))

    timezone = ZoneInfo(family.timezone)
    snapshots: list[MealMenuSnapshot] = []
    for (merchant_key, merchant_name, source_kind), rows in grouped.items():
        observed_at = max(observation.observed_at for observation, _ in rows)
        observed_local = observed_at.astimezone(timezone)
        snapshot = MealMenuSnapshot(
            family_id=family.id,
            provider_key=provider_key,
            merchant_key=merchant_key,
            merchant_name=merchant_name,
            source_kind=source_kind,
            observed_at=observed_at,
            observed_local_date=observed_local.date(),
            weekday=observed_local.weekday(),
            item_count=len(rows),
            is_complete=is_complete,
            query=None if not query else query.strip()[:160],
            source_reference=rows[0][0].source_reference,
        )
        db.add(snapshot)
        db.flush()

        observed_availability_ids: set[uuid.UUID] = set()
        for observation, ingested_item in rows:
            observed_availability_ids.add(ingested_item.availability_id)
            db.add(
                MealMenuSnapshotItem(
                    snapshot_id=snapshot.id,
                    food_item_id=ingested_item.food_item_id,
                    item_key=observation.item_key,
                    item_name=observation.item_name,
                    item_price=observation.item_price,
                    currency=observation.currency.upper(),
                    source_reference=observation.source_reference,
                )
            )

        if is_complete:
            _set_current_menu_availability(
                db,
                family_id=family.id,
                provider_key=provider_key,
                source_kind=source_kind,
                observed_availability_ids=observed_availability_ids,
            )
        snapshots.append(snapshot)

    db.flush()
    return tuple(snapshots)


def learn_weekday_menu_pattern(
    db: Session,
    *,
    family_id: uuid.UUID,
    provider_key: str,
    merchant_key: str,
) -> tuple[WeekdayMenuPattern, ...]:
    """Learn empirical weekday recurrence from complete historical menu snapshots.

    Each local calendar date counts once. When several complete snapshots exist on the
    same day, learning uses the union of dishes seen across that day. This avoids a
    later sync, after dishes have sold out, incorrectly teaching that those dishes were
    never offered on that weekday.
    """

    snapshots = db.scalars(
        select(MealMenuSnapshot)
        .options(selectinload(MealMenuSnapshot.items))
        .where(
            MealMenuSnapshot.family_id == family_id,
            MealMenuSnapshot.provider_key == provider_key,
            MealMenuSnapshot.merchant_key == merchant_key,
            MealMenuSnapshot.is_complete.is_(True),
        )
        .order_by(
            MealMenuSnapshot.observed_local_date,
            MealMenuSnapshot.observed_at,
        )
    ).all()

    items_by_date: dict[object, set[uuid.UUID]] = defaultdict(set)
    weekday_by_date: dict[object, int] = {}
    item_names: dict[uuid.UUID, str] = {}
    for snapshot in snapshots:
        weekday_by_date[snapshot.observed_local_date] = snapshot.weekday
        for item in snapshot.items:
            item_names[item.food_item_id] = item.item_name
            items_by_date[snapshot.observed_local_date].add(item.food_item_id)

    sampled_days: dict[int, int] = defaultdict(int)
    observed_days: dict[tuple[int, uuid.UUID], int] = defaultdict(int)
    for observed_date, present_food_items in items_by_date.items():
        weekday = weekday_by_date[observed_date]
        sampled_days[weekday] += 1
        for food_item_id in present_food_items:
            observed_days[(weekday, food_item_id)] += 1

    patterns: list[WeekdayMenuPattern] = []
    for (weekday, food_item_id), count in observed_days.items():
        total = sampled_days[weekday]
        frequency = (Decimal(count) / Decimal(total)).quantize(
            Decimal("0.001"),
            rounding=ROUND_HALF_UP,
        )
        patterns.append(
            WeekdayMenuPattern(
                food_item_id=food_item_id,
                item_name=item_names[food_item_id],
                weekday=weekday,
                observed_days=count,
                sampled_days=total,
                frequency=frequency,
            )
        )

    return tuple(
        sorted(
            patterns,
            key=lambda pattern: (
                pattern.weekday,
                -pattern.frequency,
                pattern.item_name.casefold(),
            ),
        )
    )
