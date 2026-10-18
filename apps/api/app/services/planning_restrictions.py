"""Explain automatic planning defaults separately from clinical prescriptions."""

import uuid
from datetime import date, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.dietary_review import FodmapReference, FoodFodmapReference, PersonHealthCondition
from app.models.food_catalog import FoodItem
from app.schemas.planning_workspace import PlanningRestrictionsRequest
from app.services.dietary_review import require_person
from app.services.meal_recommendation import _food_subjects
from app.services.nutrition_plan import compile_effective_nutrition_plan
from app.services.weekly_planning_request_cache import current_weekly_planning_cache

# Product policy explicitly requested by the Family. This is a planning profile,
# not a claim that every SIBO patient needs a permanent elimination diet.
CONDITION_PROFILES = {"sibo": "low_fodmap"}
DIET_KEYS = {"low_fodmap", "low-fodmap", "fodmap"}


def high_fodmap_foods(db: Session, family_id: uuid.UUID):
    return list(
        db.scalars(
            select(FoodItem)
            .where(
                FoodItem.is_active.is_(True),
                or_(FoodItem.family_id == family_id, FoodItem.family_id.is_(None)),
                FoodItem.id.in_(
                    select(FoodFodmapReference.food_item_id)
                    .join(FodmapReference, FodmapReference.id == FoodFodmapReference.reference_id)
                    .where(FodmapReference.classification == "high")
                ),
            )
            .order_by(FoodItem.catalog_key)
        )
    )


def active_conditions(db: Session, person_ids: list[uuid.UUID], on_date: date):
    return list(
        db.scalars(
            select(PersonHealthCondition)
            .where(
                PersonHealthCondition.person_id.in_(person_ids),
                PersonHealthCondition.status.in_(("reported", "confirmed")),
                or_(
                    PersonHealthCondition.started_on.is_(None),
                    PersonHealthCondition.started_on <= on_date,
                ),
                or_(
                    PersonHealthCondition.ended_on.is_(None),
                    PersonHealthCondition.ended_on >= on_date,
                ),
            )
            .order_by(PersonHealthCondition.person_id, PersonHealthCondition.code)
        )
    )


def condition_excluded_foods(
    db: Session, family_id: uuid.UUID, person_ids: list[uuid.UUID], on_date: date
):
    if any(
        CONDITION_PROFILES.get(c.code.casefold()) == "low_fodmap"
        for c in active_conditions(db, person_ids, on_date)
    ):
        return high_fodmap_foods(db, family_id)
    return []


def planning_restrictions(db: Session, family_id: uuid.UUID, data, *, days=7):
    for person_id in data.person_ids:
        require_person(db, family_id, person_id)
    foods = list(
        db.scalars(
            select(FoodItem).where(
                FoodItem.is_active.is_(True),
                or_(FoodItem.family_id == family_id, FoodItem.family_id.is_(None)),
            )
        )
    )
    high = high_fodmap_foods(db, family_id)
    sources = {}
    warnings = set()
    for offset in range(days):
        on_date = data.week_start + timedelta(days=offset)

        def present(person_id, meal_type, on_date=on_date):
            override = next(
                (
                    a
                    for a in data.attendance
                    if a.planning_date == on_date and a.meal_type == meal_type
                ),
                None,
            )
            return override is None or person_id in override.person_ids

        for condition in active_conditions(db, data.person_ids, on_date):
            if not any(present(condition.person_id, meal) for meal in data.meal_types):
                continue
            if condition.code.casefold() not in CONDITION_PROFILES:
                warnings.add(f"{condition.name}: sem perfil alimentar automático configurado.")
                continue
            key = f"condition:{condition.id}"
            row = sources.setdefault(
                key,
                {
                    "person_id": condition.person_id,
                    "source_id": key,
                    "source_kind": "condition",
                    "label": f"{condition.name} · perfil de planeamento FODMAP",
                    "food_item_ids": [f.id for f in high],
                    "dates": [],
                    "meal_types": data.meal_types,
                },
            )
            row["dates"].append(on_date)
        for person_id in data.person_ids:
            for meal_type in data.meal_types:
                if not present(person_id, meal_type):
                    continue
                cache = current_weekly_planning_cache(db)
                cache_key = (person_id, on_date, meal_type)
                effective = cache.effective_plans.get(cache_key) if cache else None
                if effective is None:
                    effective = compile_effective_nutrition_plan(
                        db,
                        person_id=person_id,
                        on_date=on_date,
                        meal_type=meal_type,
                    )
                    if cache:
                        cache.effective_plans[cache_key] = effective
                for rule in effective.numeric_rules:
                    if rule.operator != "exclude":
                        continue
                    selected = [
                        f.id
                        for f in foods
                        if (rule.target_type, rule.target_key) in _food_subjects(f)
                    ]
                    if rule.target_type == "diet" and rule.target_key in DIET_KEYS:
                        selected = [f.id for f in high]
                    if not selected:
                        continue
                    key = f"plan:{person_id}:{rule.id}:{meal_type}"
                    row = sources.setdefault(
                        key,
                        {
                            "person_id": person_id,
                            "source_id": key,
                            "source_kind": "diet",
                            "label": f"{rule.source.plan_title or 'Restrição pessoal'} · {rule.target_key}",
                            "food_item_ids": selected,
                            "dates": [],
                            "meal_types": [meal_type],
                        },
                    )
                    row["dates"].append(on_date)
                for guideline in effective.guidelines:
                    if guideline.target_type != "diet" or guideline.target_key not in DIET_KEYS:
                        continue
                    key = f"diet:{person_id}:{guideline.id}:{meal_type}"
                    row = sources.setdefault(
                        key,
                        {
                            "person_id": person_id,
                            "source_id": key,
                            "source_kind": "diet",
                            "label": f"{guideline.source.plan_title or 'Dieta'} · FODMAP",
                            "food_item_ids": [f.id for f in high],
                            "dates": [],
                            "meal_types": [meal_type],
                        },
                    )
                    row["dates"].append(on_date)
    return {
        "sources": list(sources.values()),
        "excluded_food_item_ids": sorted(
            {i for row in sources.values() for i in row["food_item_ids"]}, key=str
        ),
        "warnings": sorted(warnings),
    }


def automatic_excluded_foods(db, family_id, person_ids, on_date, meal_type):
    context = planning_restrictions(
        db,
        family_id,
        PlanningRestrictionsRequest(
            person_ids=person_ids,
            week_start=on_date,
            meal_types=[meal_type],
        ),
        days=1,
    )
    ids = context["excluded_food_item_ids"]
    return list(db.scalars(select(FoodItem).where(FoodItem.id.in_(ids)))) if ids else []
