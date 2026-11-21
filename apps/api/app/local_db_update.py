"""Local development schema + catalogue updates run on API startup.

Never imports/recreates the full demo dataset. Migrations and reference data
are applied in order and the schema is locked against concurrent starts.
Production/test boot does not run this module.
"""
from collections.abc import Callable

from alembic import command
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT, settings
from app.db.session import SessionLocal, engine
from app.development_plant_milk_seed import seed_development_plant_milk_options
from app.models.family import Family
from app.models.food_catalog import FoodItem

# Stable lock key: protects database schema migration across local API workers.
_LOCK_ID = 516831042096


def apply_catalogue_updates(session: Session) -> tuple[int, int]:
    """Apply non-destructive reference data to existing families only.

    Existing breakfast milk is a prerequisite. Do not seed example households,
    recipes, people or health records on an existing user database.
    """
    milk_exists = session.scalar(
        select(FoodItem.id).where(FoodItem.catalog_key == "breakfast:ingredient:milk")
    )
    if milk_exists is None:
        return (0, 0)
    families = tuple(session.scalars(select(Family).order_by(Family.id)).all())
    if not families:
        return (0, 0)
    return seed_development_plant_milk_options(session, families=families)


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
            with session_factory() as session:
                with session.begin():
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
