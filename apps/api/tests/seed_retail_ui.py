"""Synthetic package UI demo. Refuses every database except nutriflow_package_ui."""

import uuid

from sqlalchemy import select

from app.db.session import SessionLocal, engine
from app.models import Family, Person
from app.models.planning_workspace import RetailAlternative
from app.retail_alternatives_seed import import_retail_observations
from app.schemas.planning_workspace import RetailIngredientConfirmRequest
from app.services.retail_purchase import confirm_ingredient, label_fingerprint
from tests.test_retail_purchase import _effective_variant_shopping


def main():
    if engine.url.database != "nutriflow_package_ui":
        raise RuntimeError("This synthetic fixture requires nutriflow_package_ui")
    with SessionLocal() as db:
        family_id = uuid.UUID("11111111-1111-4111-8111-111111111111")
        if db.get(Family, family_id):
            print("Synthetic package fixture already exists")
            return
        family = Family(id=family_id, name="Teste de embalagens", timezone="Europe/Lisbon")
        people = [Person(family=family, first_name=name) for name in ("Ana", "Bruno")]
        db.add_all([family, *people])
        db.flush()
        import_retail_observations(db)
        product = db.scalar(
            select(RetailAlternative).where(RetailAlternative.product_key == "auchan:2749257")
        )
        fingerprint = label_fingerprint(product)
        confirmation = confirm_ingredient(
            db,
            family_id,
            product.id,
            RetailIngredientConfirmRequest(expected_fingerprint=fingerprint, label_reviewed=True),
        )
        path = f"/api/families/{family_id}"
        _effective_variant_shopping(
            db,
            (
                family,
                None,
                people,
                path,
                {"id": str(product.id), "evidence_fingerprint": fingerprint},
                str(confirmation["food_item_id"]),
            ),
        )
        print("Synthetic fixture ready: 1100 g needed, 500 g per package; no product choice saved")


if __name__ == "__main__":
    main()
