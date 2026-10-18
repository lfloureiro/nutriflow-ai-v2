import uuid
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.food_catalog import FoodCompositionSnapshot, FoodItem
from app.models.person import Person
from app.models.planning_workspace import FamilyWeekSetup, RetailAlternative
from app.schemas.planning_workspace import RetailAlternativeRead, WeekSetupRead, WeekSetupWrite
from app.services.dietary_review import require_family


def validate_week(week: date):
    if week.weekday() != 0:
        raise HTTPException(422, "Choose the Monday that starts the planning week")


def validate_food_exclusions(db: Session, family_id: uuid.UUID, ids: list[uuid.UUID]):
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate excluded foods are not allowed")
    foods = (
        db.scalars(
            select(FoodItem).where(
                FoodItem.id.in_(ids),
                FoodItem.is_active.is_(True),
                or_(FoodItem.family_id == family_id, FoodItem.family_id.is_(None)),
            )
        ).all()
        if ids
        else []
    )
    if len(foods) != len(ids):
        raise ValueError("An excluded food is unavailable in this Family")
    return foods


def setup_read(row: FamilyWeekSetup):
    return WeekSetupRead(week_start=row.week_start, version=row.version, **row.settings)


def get_setup(db: Session, family_id: uuid.UUID, week: date):
    require_family(db, family_id)
    validate_week(week)
    row = db.scalar(
        select(FamilyWeekSetup).where(
            FamilyWeekSetup.family_id == family_id,
            FamilyWeekSetup.week_start == week,
        )
    )
    return setup_read(row) if row else None


def save_setup(db: Session, family_id: uuid.UUID, week: date, data: WeekSetupWrite):
    require_family(db, family_id)
    validate_week(week)
    people = db.scalars(
        select(Person).where(
            Person.family_id == family_id,
            Person.id.in_(data.person_ids),
        )
    ).all()
    if len(people) != len(data.person_ids):
        raise HTTPException(404, "A selected Person does not belong to this Family")
    try:
        validate_food_exclusions(db, family_id, data.excluded_food_item_ids)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    keys = set()
    for entry in data.attendance:
        key = (entry.planning_date, entry.meal_type)
        if key in keys:
            raise HTTPException(422, "Duplicate meal attendance")
        keys.add(key)
        if not week <= entry.planning_date < week + timedelta(days=7):
            raise HTTPException(422, "Attendance must belong to the selected week")
        if entry.meal_type not in data.meal_types or not set(entry.person_ids) <= set(
            data.person_ids
        ):
            raise HTTPException(422, "Attendance must use selected meals and people")
    settings = data.model_dump(mode="json", exclude={"expected_version"})
    try:
        if data.expected_version == 0:
            row = FamilyWeekSetup(family_id=family_id, week_start=week, settings=settings)
            db.add(row)
            db.flush()
        else:
            row = db.scalar(
                select(FamilyWeekSetup).where(
                    FamilyWeekSetup.family_id == family_id,
                    FamilyWeekSetup.week_start == week,
                )
            )
            if row is None:
                raise HTTPException(409, "Planning setup changed; reload")
            result = db.execute(
                update(FamilyWeekSetup)
                .where(
                    FamilyWeekSetup.id == row.id,
                    FamilyWeekSetup.version == data.expected_version,
                )
                .values(settings=settings, version=data.expected_version + 1)
            )
            if result.rowcount != 1:
                raise HTTPException(409, "Planning setup changed; reload")
            db.refresh(row)
        db.commit()
        db.refresh(row)
        return setup_read(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Planning setup changed; reload") from exc


def retail_alternatives(db: Session, family_id: uuid.UUID):
    require_family(db, family_id)
    foods = db.scalars(
        select(FoodItem).where(
            FoodItem.is_active.is_(True),
            or_(FoodItem.family_id == family_id, FoodItem.family_id.is_(None)),
        )
    ).all()
    foods_by_key = {}
    for food in foods:
        foods_by_key.setdefault(food.catalog_key, []).append(food.id)
    from app.models.retail_confirmation import RetailIngredientConfirmation
    from app.services.retail_purchase import (
        confirmation_current,
        confirmation_issue,
        label_fingerprint,
    )

    confirmations = db.scalars(
        select(RetailIngredientConfirmation)
        .where(RetailIngredientConfirmation.family_id == family_id)
        .options(
            selectinload(RetailIngredientConfirmation.retail_product),
            selectinload(RetailIngredientConfirmation.food_item)
            .selectinload(FoodItem.compositions)
            .selectinload(FoodCompositionSnapshot.nutrients),
        )
    ).all()
    confirmed = {
        row.retail_product_id: row.food_item_id
        for row in confirmations
        if confirmation_current(row)
    }
    result = []
    for product in db.scalars(
        select(RetailAlternative).order_by(
            RetailAlternative.alternative_group,
            RetailAlternative.retailer,
        )
    ):
        read = RetailAlternativeRead.model_validate(product)
        read.applicable_food_item_ids = [
            food_id
            for key in dict.fromkeys(product.source_food_catalog_keys)
            for food_id in foods_by_key.get(key, [])
        ]
        read.evidence_fingerprint = label_fingerprint(product)
        read.ingredient_confirmation_issue = confirmation_issue(product)
        read.confirmed_food_item_id = confirmed.get(product.id)
        if (
            read.confirmed_food_item_id
            and read.confirmed_food_item_id not in read.applicable_food_item_ids
        ):
            read.applicable_food_item_ids.append(read.confirmed_food_item_id)
        result.append(read)
    return result
