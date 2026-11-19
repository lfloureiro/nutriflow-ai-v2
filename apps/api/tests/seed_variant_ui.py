"""Explicit synthetic UI fixture. Refuses every database except the isolated test DB.

Run from apps/api with DATABASE_URL pointing to nutriflow_review_test:
python -m tests.seed_variant_ui
"""

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.db.session import SessionLocal, engine
from app.models import DailyNutritionState, Family, Person
from tests.test_recipe_variants import pilot


def seed():
    if engine.url.database != "nutriflow_review_test":
        raise RuntimeError("UI fixtures may only be seeded in nutriflow_review_test")
    with SessionLocal() as db:
        existing = db.scalar(select(Family).where(Family.name == "TESTE interface variantes"))
        if existing:
            ensure_states(db, existing)
            db.commit()
            return {"family_id": str(existing.id), "reused": True}
        family, _, _, _, recipe, _, _ = pilot.__wrapped__(db)
        family.name = "TESTE interface variantes"
        recipe.description = (
            "Synthetic interface fixture. Not a clinical recipe or real Family data."
        )
        ensure_states(db, family)
        db.commit()
        return {"family_id": str(family.id), "base_recipe_id": str(recipe.id), "reused": False}


def ensure_states(db, family):
    for p in db.scalars(select(Person).where(Person.family_id == family.id)):
        for offset in range(7):
            day = date(2030, 1, 7) + timedelta(days=offset)
            existing = db.scalar(
                select(DailyNutritionState).where(
                    DailyNutritionState.person_id == p.id, DailyNutritionState.state_date == day
                )
            )
            if existing:
                if existing.calculation_version == "synthetic-ui-variant":
                    existing.calculation_version = "demo-energy-budget-v1"
                    existing.calculation_inputs = {
                        "source": "synthetic-development-demo",
                        "purpose": "isolated-variant-ui",
                    }
                continue
            db.add(
                DailyNutritionState(
                    person_id=p.id,
                    state_date=day,
                    timezone="Europe/Lisbon",
                    energy_consumed_kcal=Decimal(0),
                    energy_planned_kcal=Decimal(0),
                    energy_remaining_min_kcal=Decimal(0),
                    energy_remaining_max_kcal=Decimal(5000),
                    calculation_version="demo-energy-budget-v1",
                    calculation_inputs={
                        "source": "synthetic-development-demo",
                        "purpose": "isolated-variant-ui",
                    },
                    computed_at=datetime(2030, 1, 1, tzinfo=UTC),
                )
            )


if __name__ == "__main__":
    print(json.dumps(seed()))
