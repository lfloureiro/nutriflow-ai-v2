"""Local development schema + catalogue updates run on API startup.

Never imports/recreates the full demo dataset. Migrations and reference data
are applied in order and the schema is locked against concurrent starts.
Production/test boot does not run this module.
"""
from collections.abc import Callable

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT, settings
from app.db.session import SessionLocal, engine
from app.development_breakfast_seed import RECIPES, seed_development_breakfast_catalog
from app.development_bread_review_seed import seed_development_bread_candidates
from app.development_plant_milk_seed import seed_development_plant_milk_options
from app.models.family import Family
from app.models.food_catalog import Recipe
from app.models.meal_candidate_planning_profile import MealCandidatePlanningProfile

# Stable lock key: protects database schema migration across local API workers.
_LOCK_ID = 516831042096


def apply_catalogue_updates(session: Session) -> tuple[int, int]:
    """Apply non-destructive reference data to existing families only.

    Do not seed example households, people, plans or health records. Reference
    breakfast recipes are shared and their stable keys prevent duplicates.
    They are inserted only if the catalogue or a family's planning profiles
    are incomplete, so normal restarts do not rewrite existing recipes.
    """
    families = tuple(session.scalars(select(Family).order_by(Family.id)).all())
    if not families:
        return (0, 0)

    recipe_keys = [f"breakfast:recipe:{definition.key}" for definition in RECIPES]
    existing_keys = set(
        session.scalars(
            select(Recipe.recipe_key).where(Recipe.recipe_key.in_(recipe_keys))
        ).all()
    )
    missing_profiles = any(
        session.scalar(
            select(func.count(MealCandidatePlanningProfile.id)).where(
                MealCandidatePlanningProfile.family_id == family.id,
                MealCandidatePlanningProfile.source == "development-breakfast",
            )
        ) < len(RECIPES)
        for family in families
    )
    if len(existing_keys) != len(RECIPES) or missing_profiles:
        seed_development_breakfast_catalog(session, families=families)
        session.flush()

    milk_summary = seed_development_plant_milk_options(session, families=families)
    # Review-only product candidates; never enable a bread swap on startup.
    seed_development_bread_candidates(session, families=families)
    return milk_summary


def apply_local_updates(
    *,
    migrate: Callable[[], None] | None = None,
    session_factory: Callable[[], Session] = SessionLocal,
) -> tuple[int, int]:
    """Run ordered schema and catalogue patches before accepting API traffic.

    PostgreSQL session-level lock spans Alembic's separate connection and the
    data-update transaction, preventing simultaneous startup updates.
    """
    if settings.app_env != "development":
        raise RuntimeError("Local database auto-update is restricted to APP_ENV=development")

    if migrate is None:
        def migrate() -> None:
            cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
            command.upgrade(cfg, "head")

    with engine.connect() as lock_connection:
        lock_connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": _LOCK_ID})
        lock_connection.commit()
        try:
            migrate()
            with session_factory() as session, session.begin():
                result = apply_catalogue_updates(session)
            return result
        finally:
            lock_connection.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": _LOCK_ID}
            )
            lock_connection.commit()


def main() -> None:
    updated = apply_local_updates()
    print(
        "NutriFlow local database is current: schema migrations and "
        f"plant-milk catalogue ({updated[0]} source/target ingredients, "
        f"{updated[1]} automatic alternatives)."
    )


if __name__ == "__main__":
    main()
