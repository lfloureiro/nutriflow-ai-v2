"""Retail bread alternatives awaiting ingredient/serving FODMAP review.

These are named retailer products, not generic clinically approved ingredients.
Catalogue entries allow recipe authors to choose a specific bread for review.
Do not add nutritional composition or enable automatic substitution on import.
"""
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import FoodItem
from app.models.food_transformation_profile import FoodTransformationProfile

NAMESPACE = uuid.UUID("a32ff6d2-8e90-4ab8-9d42-b4b6c3fd4a12")
SOURCE = "development-bread-review"
SOURCE_REFERENCE = "pt-retail-bread-labels-2026-11-22"
GROUP = "bread-for-breakfast"
SOURCE_BREAD_KEY = "breakfast:ingredient:toast-bread"


@dataclass(frozen=True)
class BreadCandidate:
    key: str
    name: str
    brand: str
    store: str
    pack_g: int
    url: str
    ingredients: str
    review_reason: str


CANDIDATES = (
    BreadCandidate(
        key="bread-review:auchan-white-400g",
        name="Pão de forma Auchan sem glúten 400 g",
        brand="Auchan",
        store="Auchan Portugal",
        pack_g=400,
        url="https://www.auchan.pt/pt/alimentacao/mercearia/tostas-e-pao-embalado/pao-embalado/pao-de-forma-auchan-sem-gluten-400g/3509556.html",
        ingredients=(
            "Água, farinha de arroz, fécula de batata, fécula de tapioca, óleo "
            "de colza, farinha de milho, casca de psílio, levedura, xarope "
            "dourado, glicerol, clara de ovo em pó, sal, "
            "hidroxipropilmetilcelulose, amido de milho, fibras vegetais."
        ),
        review_reason=(
            "Confirmar origem das fibras vegetais, xarope dourado, "
            "rótulo atual, alergénios e dose tolerada."
        ),
    ),
    BreadCandidate(
        key="bread-review:schar-white-sliced-250g",
        name="Pão branco fatiado sem glúten Schär 250 g",
        brand="Schär",
        store="Continente Portugal",
        pack_g=250,
        url="https://www.continente.pt/produto/pao-branco-fatiado-sem-gluten-schar-6541632.html",
        ingredients=(
            "Água, amido de milho, farinha de arroz, fibra vegetal "
            "(psílio, cítrica), hidroxipropilmetilcelulose, óleo de "
            "girassol, proteína de soja, levedura, sal, açúcar, ácido cítrico."
        ),
        review_reason=(
            "Confirmar soja e possíveis alergénios, composição do rótulo "
            "recebido e porção individual."
        ),
    ),
    BreadCandidate(
        key="bread-review:auchan-white-300g",
        name="Pão Auchan de forma sem glúten 300 g",
        brand="Auchan",
        store="Auchan Portugal",
        pack_g=300,
        url="https://www.auchan.pt/pt/alimentacao/mercearia/tostas-e-pao-embalado/pao-embalado/pao-auchan-forma-sem-gluten-300g/3241708.html",
        ingredients=(
            "Água, amido de milho, massa lêveda de arroz, amido de tapioca, "
            "farinha de trigo-sarraceno, óleo de girassol, xarope de arroz, "
            "fibras vegetais (psílio, bambu), farinha de quinoa, proteína "
            "de arroz, levedura, açúcar, sal, espessante, emulsionante, "
            "aroma e conservantes."
        ),
        review_reason=(
            "Confirmar fibras, aditivos, rótulo recebido e porção individual."
        ),
    ),
)


def _id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"{kind}:{key}")


def seed_development_bread_candidates(
    session: Session, *, families: tuple[Family, ...]
) -> int:
    """Insert review candidates and disabled bread-swap profiles, idempotently.

    Never modify a non-owned catalogue entry or an existing Family decision.
    Source bread is linked for future review, but no replacement is approved
    automatically; no fake nutrition or clinical low-FODMAP claim is stored.
    """
    sources = (SOURCE_BREAD_KEY, *(item.key for item in CANDIDATES))
    for key in sources:
        item = session.scalar(select(FoodItem).where(FoodItem.catalog_key == key))
        if key == SOURCE_BREAD_KEY:
            if item is None:
                raise ValueError("Breakfast source bread must be seeded first.")
        elif item is None:
            candidate = next(entry for entry in CANDIDATES if entry.key == key)
            item = FoodItem(
                id=_id("food", key),
                catalog_key=key,
                family_id=None,
                food_kind="ingredient",
                name=candidate.name,
                brand=candidate.brand,
                suitable_meal_types=["breakfast"],
                source=SOURCE,
                source_reference=candidate.url,
                description=(
                    f"Fornecedor: {candidate.store}. Embalagem: {candidate.pack_g} g. "
                    f"Ingredientes publicados: {candidate.ingredients} "
                    f"FODMAP por validar; candidato para revisão, não certificado "
                    f"nem aprovado para substituição automática. "
                    f"{candidate.review_reason} Fonte consultada: 2026-11-22."
                ),
                is_active=True,
            )
            session.add(item)
        session.flush()
        for family in families:
            profile_id = _id("profile", f"{family.id}:{key}")
            existing = session.scalar(
                select(FoodTransformationProfile).where(
                    FoodTransformationProfile.family_id == family.id,
                    FoodTransformationProfile.food_item_id == item.id,
                )
            )
            if existing is not None:
                continue
            session.add(
                FoodTransformationProfile(
                    id=profile_id,
                    family_id=family.id,
                    food_item_id=item.id,
                    substitution_group=GROUP,
                    typical_quantity=Decimal(60),
                    typical_unit="g",
                    auto_transform_enabled=False,
                    source=SOURCE,
                    source_reference=SOURCE_REFERENCE,
                )
            )
        session.flush()
    return len(CANDIDATES)
