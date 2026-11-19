"""Explicit, idempotent import of a small public Monash educational selection.

No scraping of app/calculator data, no invented laboratory amounts, no recipe writes.
Run: python -m app.fodmap_guidance_seed --family-id UUID
"""

import argparse
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.dietary_review import (
    FodmapReference,
    FoodFodmapReference,
    RecipeSubstitutionReview,
)
from app.models.food_catalog import FoodItem, Recipe, RecipeIngredient
from app.services.dietary_review import require_family

FOODS_URL = "https://www.monashfodmap.com/about-fodmap-and-ibs/high-and-low-fodmap-foods/"
AROMATICS_URL = "https://www.monashfodmap.com/blog/cooking-with-onion-and-garlic-myths-and/"
VERSION = "public-summary-2026-10-18"

# key, Portuguese/English names, public classification, reported groups, source.
# These are educational facts, not a complete reproduction of the source table.
REFERENCE_ROWS = [
    ("garlic", "Alho", "Garlic", "high", ["fructans"], FOODS_URL),
    ("onion", "Cebola", "Onion", "high", ["fructans"], FOODS_URL),
    ("leek", "Alho-francês", "Leek", "high", ["fructans"], FOODS_URL),
    ("mushrooms", "Cogumelos", "Mushrooms", "high", ["mannitol"], FOODS_URL),
    ("kidney-beans", "Feijão vermelho", "Red kidney beans", "high", ["gos"], FOODS_URL),
    ("milk", "Leite de vaca", "Cow's milk", "high", ["lactose"], FOODS_URL),
    ("yogurt", "Iogurte", "Yoghurt", "high", ["lactose"], FOODS_URL),
    ("apple", "Maçã", "Apple", "high", ["excess_fructose", "sorbitol"], FOODS_URL),
    ("wheat-pasta", "Massa de trigo", "Wheat pasta", "high", ["fructans"], FOODS_URL),
    ("wheat-muesli", "Muesli com trigo", "Wheat muesli", "high", ["fructans"], FOODS_URL),
    ("lactose-free-milk", "Leite sem lactose", "Lactose-free milk", "low", [], FOODS_URL),
    ("rice-corn-pasta", "Massa de arroz/milho", "Rice/corn pasta", "low", [], FOODS_URL),
    ("carrot", "Cenoura", "Carrot", "low", [], FOODS_URL),
    ("potato", "Batata", "Potato", "low", [], FOODS_URL),
    ("orange", "Laranja", "Orange", "low", [], FOODS_URL),
    ("kiwi", "Kiwi", "Kiwifruit", "low", [], FOODS_URL),
    ("oats", "Aveia simples", "Oats", "low", [], FOODS_URL),
    ("walnuts", "Nozes", "Walnuts", "low", [], FOODS_URL),
    (
        "chives",
        "Cebolinho / parte verde de cebolinha",
        "Chives / green spring onion tops",
        "low",
        [],
        AROMATICS_URL,
    ),
    (
        "garlic-oil",
        "Azeite aromatizado com alho, sem pedaços",
        "Garlic-infused oil, no pieces",
        "low",
        [],
        AROMATICS_URL,
    ),
    ("ginger", "Gengibre", "Ginger", "low", [], AROMATICS_URL),
    ("herbs", "Ervas frescas simples", "Plain fresh herbs", "low", [], AROMATICS_URL),
]

# Explicitly audited catalogue identities; no runtime classification from names.
MAPPINGS = {
    "legacy-v1:ingredient:4": "garlic",
    "legacy-v1:ingredient:5": "garlic",
    "legacy-v1:ingredient:6": "garlic",
    "legacy-v1:ingredient:7": "leek",
    "legacy-v1:ingredient:29": "onion",
    "legacy-v1:ingredient:30": "onion",
    "legacy-v1:ingredient:31": "onion",
    "legacy-v1:ingredient:32": "chives",
    "legacy-v1:ingredient:33": "carrot",
    "legacy-v1:ingredient:39": "mushrooms",
    "legacy-v1:ingredient:40": "mushrooms",
    "legacy-v1:ingredient:74": "kidney-beans",
    "legacy-v1:ingredient:77": "milk",
    "legacy-v1:ingredient:54": "wheat-pasta",
    "legacy-v1:ingredient:61": "wheat-pasta",
    "legacy-v1:ingredient:80": "wheat-pasta",
    "legacy-v1:ingredient:81": "wheat-pasta",
    "legacy-v1:ingredient:85": "wheat-pasta",
    "legacy-v1:ingredient:18": "potato",
    "legacy-v1:ingredient:19": "potato",
    "breakfast:ingredient:milk": "milk",
    "breakfast:ingredient:apple": "apple",
    "breakfast:ingredient:natural-yogurt": "yogurt",
    "breakfast:ingredient:greek-yogurt": "yogurt",
    "breakfast:ingredient:muesli": "wheat-muesli",
}

REPLACEMENTS = {
    "garlic": (
        "garlic-oil",
        (
            "Usar na fração de azeite da receita; não trocar alho por azeite "
            "grama por grama. Produto sem pedaços; rever todos os outros aromáticos."
        ),
    ),
    "onion": (
        "chives",
        (
            "Usar cebolinho ou só a parte verde da cebolinha; pesar e validar dose. "
            "Rever alho e produtos compostos na mesma preparação."
        ),
    ),
    "leek": ("chives", "Confirmar parte do alho-francês e dose; alternativa culinária por rever."),
    "mushrooms": (
        "carrot",
        (
            "Alternativa culinária; confirmar espécie dos cogumelos e "
            "quantidade dos legumes na porção individual."
        ),
    ),
    "milk": (
        "lactose-free-milk",
        (
            "Confirmar produto, quantidade, fortificação e restantes "
            "ingredientes. Sem lactose não significa sem proteína do leite."
        ),
    ),
    "wheat-pasta": (
        "rice-corn-pasta",
        "Confirmar lista de ingredientes e dose; sem glúten não é garantia de baixo teor FODMAP.",
    ),
    "apple": (
        "kiwi",
        (
            "Alternativa para rever na dose individual; não assumir equivalência "
            "em peso, energia ou tolerância."
        ),
    ),
    "wheat-muesli": (
        "oats",
        (
            "Confirmar composição do muesli antes da alteração; avaliar "
            "aveia simples sem mel, fruta seca ou inulina na dose adequada."
        ),
    ),
}

# Editorial cooking ideas for opaque products. These deliberately have no food
# classification/reference link and must never be interpreted as tested replacements.
REVIEW_ONLY = {
    "legacy-v1:ingredient:24": (
        "Caldo caseiro com ingredientes identificados",
        "Confirmar alho, cebola e outros ingredientes do caldo.",
    ),
    "legacy-v1:ingredient:25": (
        "Caldo caseiro com ingredientes identificados",
        "Confirmar alho, cebola e outros ingredientes do caldo.",
    ),
    "legacy-v1:ingredient:26": (
        "Caldo caseiro com ingredientes identificados",
        "Confirmar alho, cebola e outros ingredientes do caldo.",
    ),
    "legacy-v1:ingredient:135": (
        "Molho caseiro de ervas, sem sopa de cebola",
        "Rever todos os ingredientes do molho; definir espessante e dose.",
    ),
    "legacy-v1:ingredient:94": (
        "Natas sem lactose, com rótulo verificado",
        "Verificar produto e porção; não extrapolar dados de leite para natas.",
    ),
    "legacy-v1:ingredient:58": (
        "Espessante de arroz ou milho, por validar",
        "Rever função culinária, rótulo e quantidade; não assumir troca 1:1.",
    ),
    "legacy-v1:ingredient:75": (
        "Acompanhamento de arroz ou batata, por definir",
        (
            "Rever dose do grão e forma de conservação; preservar equilíbrio "
            "proteico e fibra ao escolher outro acompanhamento."
        ),
    ),
    "legacy-v1:ingredient:74": (
        "Acompanhamento de arroz ou batata, por definir",
        (
            "Rever dose do feijão e forma de conservação; preservar equilíbrio "
            "proteico e fibra ao escolher outro acompanhamento."
        ),
    ),
    "legacy-v1:ingredient:8": (
        "Almôndegas caseiras com composição identificada",
        "Confirmar pão, leite, alho e cebola do preparado atual e da alternativa.",
    ),
    "legacy-v1:ingredient:70": (
        "Hambúrguer simples com composição identificada",
        "Confirmar rótulo e temperos, incluindo alho e cebola.",
    ),
    "legacy-v1:ingredient:134": (
        "Proteína simples e tempero identificados",
        "Rever composição das salsichas e da receita completa.",
    ),
    "legacy-v1:ingredient:86": (
        "Tempero simples com composição identificada",
        "Confirmar se a massa de pimentão contém alho ou outros ingredientes.",
    ),
    "legacy-v1:ingredient:145": (
        "Mistura de legumes identificados e pesados",
        "Identificar cada legume, preparação e porção; não classificar a mistura pelo nome.",
    ),
}


def import_public_guidance(db: Session, family_id: uuid.UUID) -> dict[str, int]:
    require_family(db, family_id)
    refs = {r.reference_key: r for r in db.scalars(select(FodmapReference))}
    imported = 0
    for key, pt, en, classification, groups, url in REFERENCE_ROWS:
        if key not in refs:
            row = FodmapReference(
                reference_key=key,
                name_pt=pt,
                name_en=en,
                classification=classification,
                fodmap_groups=groups,
                preparation="generic; product/part/preparation not verified",
                evidence_kind="public_educational_summary",
                source_name="Monash University",
                source_url=url,
                source_version=VERSION,
                retrieved_on=date(2026, 10, 18),
                notes_pt="Orientação geral publicada; não é medição deste produto nem limite "
                "por porção. Validar espécie, preparação, rótulo e dose. Uma categoria "
                "baixa não certifica a receita ou a tolerância individual.",
                notes_en="Published general guidance, not a measurement of this product or a "
                "serving limit. Verify species, preparation, label and portion. A low "
                "category does not certify a recipe or individual tolerance.",
            )
            db.add(row)
            db.flush()
            refs[key] = row
            imported += 1
    links = set(
        db.execute(
            select(
                FoodFodmapReference.food_item_id,
                FoodFodmapReference.reference_id,
            )
        ).all()
    )
    for food in db.scalars(select(FoodItem).where(FoodItem.catalog_key.in_(MAPPINGS))):
        reference = refs[MAPPINGS[food.catalog_key]]
        if (food.id, reference.id) not in links:
            db.add(
                FoodFodmapReference(
                    food_item_id=food.id,
                    reference_id=reference.id,
                    mapping_basis="curated category association; exact product and dose unverified",
                )
            )
    existing = set(
        db.execute(
            select(
                RecipeSubstitutionReview.recipe_ingredient_id,
                RecipeSubstitutionReview.proposal_key,
            ).where(RecipeSubstitutionReview.family_id == family_id)
        ).all()
    )
    proposed = 0
    for ingredient, food in db.execute(
        select(RecipeIngredient, FoodItem)
        .join(FoodItem, FoodItem.id == RecipeIngredient.food_item_id)
        .join(Recipe, Recipe.id == RecipeIngredient.recipe_id)
        .where(
            Recipe.is_active.is_(True), (Recipe.family_id == family_id) | Recipe.family_id.is_(None)
        )
    ):
        group = MAPPINGS.get(food.catalog_key)
        if group not in REPLACEMENTS and food.catalog_key not in REVIEW_ONLY:
            continue
        reference_id = None
        if group in REPLACEMENTS:
            target, notes = REPLACEMENTS[group]
            key = f"public-guidance-v1:{target}"
            name = refs[target].name_pt
            reference_id = refs[target].id
        else:
            name, notes = REVIEW_ONLY[food.catalog_key]
            key = "editorial-review-v1"
            notes = "Hipótese culinária, sem confirmação FODMAP. " + notes
        if (ingredient.id, key) in existing:
            continue
        db.add(
            RecipeSubstitutionReview(
                family_id=family_id,
                recipe_ingredient_id=ingredient.id,
                proposal_key=key,
                replacement_name=name,
                reference_id=reference_id,
                status="proposed",
                notes=notes + " Proposta por rever; quantidade e composição "
                "nutricional não calculadas. Avaliar o conjunto de alterações para toda a família.",
            )
        )
        proposed += 1
    db.commit()
    return {"new_references": imported, "new_proposals": proposed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family-id", required=True, type=uuid.UUID)
    args = parser.parse_args()
    with SessionLocal() as db:
        print(import_public_guidance(db, args.family_id))


if __name__ == "__main__":
    main()
