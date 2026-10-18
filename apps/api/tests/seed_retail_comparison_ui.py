"""Prepare replenishment and store comparison only in the synthetic UI database."""

import uuid
from datetime import date

from sqlalchemy import select

from app.db.session import SessionLocal, engine
from app.models import Family
from app.models.pantry_stock import PantryStockLot
from app.services.pantry_shopping import refresh_shopping_list
from tests.seed_retail_ui import main as seed_base


def main():
    if engine.url.database != "nutriflow_package_ui":
        raise RuntimeError("This synthetic fixture requires nutriflow_package_ui")
    seed_base()
    with SessionLocal() as db:
        family = db.get(Family, uuid.UUID("11111111-1111-4111-8111-111111111111"))
        if family is None:
            raise RuntimeError("Synthetic family not found")
        for lot in db.scalars(select(PantryStockLot).where(PantryStockLot.family_id == family.id)):
            lot.is_available = False  # Simulate consumed stock without deleting receipt history.
        db.commit()
        refresh_shopping_list(db, family, start_date=date(2030, 1, 7), days=7)
        print("Synthetic replenishment comparison ready; no production data changed")


if __name__ == "__main__":
    main()
