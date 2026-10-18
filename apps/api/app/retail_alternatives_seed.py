"""Import reviewed retailer observations; no live stock or FODMAP certification."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.dietary_review import FodmapReference
from app.models.planning_workspace import RetailAlternative

PASTA_KEYS = [f"legacy-v1:ingredient:{v}" for v in (54, 61, 80, 81, 85)]
ROWS = [
    {
        "product_key": "auchan:2749257",
        "retailer": "Auchan",
        "name": "Esparguete Auchan sem glúten 500 g",
        "alternative_group": "rice-corn-pasta",
        "source_food_catalog_keys": PASTA_KEYS,
        "product_url": "https://www.auchan.pt/pt/biologicos-e-alternativas/sem-gluten/mercearia-sem-gluten/massas-e-farinhas-sem-gluten/massa-auchan-esparguete-sem-gluten-500g/2749257.html",
        "pack_quantity": Decimal(500),
        "pack_unit": "g",
        "observed_price": Decimal("1.75"),
        "ingredient_summary": "Milho branco 65%, milho amarelo 29,25%, arroz 5%; emulsionante E471.",
        "evidence_level": "retailer_ingredients_and_nutrition",
        "nutrition_per_100": {
            "reference_unit": "g",
            "energy_kcal": "360",
            "protein_g": "5.7",
            "carbohydrate_g": "81",
            "fat_g": "1",
            "fiber_g": "2.1",
            "salt_g": "0.2",
        },
    },
    {
        "product_key": "continente:5884054",
        "retailer": "Continente",
        "name": "Esparguete Rummo sem glúten 400 g",
        "alternative_group": "rice-corn-pasta",
        "source_food_catalog_keys": PASTA_KEYS,
        "product_url": "https://www.continente.pt/produto/massa-esparguete-sem-gluten-rummo-5884054.html",
        "pack_quantity": Decimal(400),
        "pack_unit": "g",
        "observed_price": Decimal("3.08"),
        "ingredient_summary": "Descrição comercial: milho e arroz integral. Lista completa de ingredientes por confirmar.",
        "evidence_level": "retailer_description_only",
        "nutrition_per_100": None,
    },
    {
        "product_key": "auchan:2945855",
        "retailer": "Auchan",
        "name": "Natas Auchan para culinária sem lactose 200 ml",
        "alternative_group": "lactose-free-cream",
        "source_food_catalog_keys": ["legacy-v1:ingredient:94"],
        "product_url": "https://www.auchan.pt/pt/alimentacao/produtos-lacteos/natas-bechamel-e-chantilly/natas/nata-uht-auchan-para-culinaria-sem-lactose-200ml/2945855.html",
        "pack_quantity": Decimal(200),
        "pack_unit": "ml",
        "observed_price": Decimal("0.85"),
        "ingredient_summary": "Nata com 20% de matéria gorda e estabilizador E407. Lactose declarada <0,01 g/100 ml. Contém leite.",
        "evidence_level": "retailer_ingredients_and_nutrition",
        "nutrition_per_100": {
            "reference_unit": "ml",
            "energy_kcal": "206",
            "protein_g": "2.6",
            "carbohydrate_g": "3.8",
            "fat_g": "20",
            "salt_g": "0.1",
        },
    },
    {
        "product_key": "continente:8163556",
        "retailer": "Continente",
        "name": "Leite Agros meio-gordo sem lactose 6 × 1 l",
        "alternative_group": "lactose-free-milk",
        "source_food_catalog_keys": ["legacy-v1:ingredient:77", "breakfast:ingredient:milk"],
        "product_url": "https://www.continente.pt/produto/leite-meio-gordo-sem-lactose-agros-8163556.html",
        "pack_quantity": Decimal(6000),
        "pack_unit": "ml",
        "observed_price": Decimal("7.50"),
        "ingredient_summary": "Produto identificado como leite sem lactose; composição e informação nutricional por confirmar no rótulo. Contém leite.",
        "evidence_level": "retailer_description_only",
        "nutrition_per_100": None,
    },
    {
        "product_key": "continente:5333298",
        "retailer": "Continente",
        "name": "Farinha de arroz Espiga 500 g",
        "alternative_group": "rice-corn-thickener",
        "source_food_catalog_keys": ["legacy-v1:ingredient:58"],
        "product_url": "https://www.continente.pt/produto/farinha-de-arroz-espiga-5333298.html",
        "pack_quantity": Decimal(500),
        "pack_unit": "g",
        "observed_price": Decimal("0.98"),
        "ingredient_summary": "Farinha de arroz identificada na descrição; lista integral e nutrição por confirmar. Rever função culinária e dose; não assumir equivalência com trigo.",
        "evidence_level": "retailer_description_only",
        "nutrition_per_100": None,
    },
    {
        "product_key": "continente:6556965",
        "retailer": "Continente",
        "name": "Farinha de arroz Origens Bio 200 g",
        "alternative_group": "rice-corn-thickener",
        "source_food_catalog_keys": ["legacy-v1:ingredient:58"],
        "product_url": "https://www.continente.pt/produto/farinha-de-arroz-origens-bio-6556965.html",
        "pack_quantity": Decimal(200),
        "pack_unit": "g",
        "observed_price": Decimal("2.00"),
        "ingredient_summary": "Descrição identifica arroz integral biológico. Rótulo e nutrição por confirmar; quantidade de espessamento por validar.",
        "evidence_level": "retailer_description_only",
        "nutrition_per_100": None,
    },
    {
        "product_key": "continente:5422373",
        "retailer": "Continente",
        "name": "Amido de milho Maizena sem glúten 700 g",
        "alternative_group": "rice-corn-thickener",
        "source_food_catalog_keys": ["legacy-v1:ingredient:58"],
        "product_url": "https://www.continente.pt/produto/farinha-amido-de-milho-sem-gluten-maizena-5422373.html",
        "pack_quantity": Decimal(700),
        "pack_unit": "g",
        "observed_price": Decimal("3.59"),
        "ingredient_summary": "Amido de milho para espessar identificado na descrição. Rótulo completo por confirmar; rever quantidade e preparação.",
        "evidence_level": "retailer_description_only",
        "nutrition_per_100": None,
    },
    {
        "product_key": "auchan:3452448",
        "retailer": "Auchan",
        "name": "Farinha de arroz Auchan sem glúten 500 g",
        "alternative_group": "rice-corn-thickener",
        "source_food_catalog_keys": ["legacy-v1:ingredient:58"],
        "product_url": "https://www.auchan.pt/pt/alimentacao/mercearia/farinha/farinha-trigo/farinha-auchan-de-arroz-sem-gluten-500-g/3452448.html",
        "pack_quantity": Decimal(500),
        "pack_unit": "g",
        "observed_price": Decimal("2.29"),
        "ingredient_summary": "Farinha de arroz; possível vestígio de ovo. Tabela online inteiramente a zero: rejeitada como composição utilizável; confirmar rótulo e dose.",
        "evidence_level": "retailer_ingredients_only",
        "nutrition_per_100": None,
    },
    {
        "product_key": "auchan:3704357",
        "retailer": "Auchan",
        "name": "Cebolinho Auchan Bio desidratado 4 g",
        "alternative_group": "chives-seasoning",
        "source_food_catalog_keys": [f"legacy-v1:ingredient:{i}" for i in (29, 30, 31)],
        "product_url": "https://www.auchan.pt/pt/alimentacao/mercearia/sal-ervas-e-temperos/ervas-e-misturas/cebolinho-auchan-bio-frasco-4g/3704357.html",
        "pack_quantity": Decimal(4),
        "pack_unit": "g",
        "observed_price": Decimal("0.99"),
        "ingredient_summary": "Cebolinho biológico desidratado; possíveis vestígios de aipo e mostarda. Não equivale em peso ao fresco nem substitui toda uma sopa de cebola.",
        "evidence_level": "retailer_ingredients_only",
        "nutrition_per_100": None,
    },
    {
        "product_key": "auchan:3921275",
        "retailer": "Auchan",
        "name": "Iogurte natural magro Auchan sem lactose 4 × 125 g",
        "alternative_group": "lactose-free-yogurt",
        "source_food_catalog_keys": [
            "breakfast:ingredient:natural-yogurt",
            "breakfast:ingredient:greek-yogurt",
        ],
        "product_url": "https://www.auchan.pt/pt/alimentacao/produtos-lacteos/sem-lactose/iogurte-sem-lactose/iogurte-natural-magro-auchan-sem-lactose-4x125g/3921275.html",
        "pack_quantity": Decimal(500),
        "pack_unit": "g",
        "observed_price": Decimal("1.28"),
        "ingredient_summary": "Leite magro, leite em pó magro, lactase e fermentos láticos. Contém leite; rever textura e composição se substituir iogurte grego.",
        "evidence_level": "retailer_ingredients_and_nutrition",
        "nutrition_per_100": {
            "reference_unit": "g",
            "energy_kcal": "38",
            "protein_g": "4",
            "carbohydrate_g": "5.1",
            "fat_g": "0.2",
            "salt_g": "0.15",
        },
    },
    {
        "product_key": "continente:7424578",
        "retailer": "Continente",
        "name": "Iogurte magro natural sem lactose Continente Equilíbrio 4 × 125 g",
        "alternative_group": "lactose-free-yogurt",
        "source_food_catalog_keys": [
            "breakfast:ingredient:natural-yogurt",
            "breakfast:ingredient:greek-yogurt",
        ],
        "product_url": "https://www.continente.pt/produto/iogurte-magro-natural-sem-lactose-continente-equilibrio-7424578.html",
        "pack_quantity": Decimal(500),
        "pack_unit": "g",
        "observed_price": Decimal("1.29"),
        "ingredient_summary": "Iogurte natural sem lactose identificado comercialmente. Ingredientes e nutrição por confirmar na embalagem; contém leite.",
        "evidence_level": "retailer_description_only",
        "nutrition_per_100": None,
    },
]


def import_retail_observations(db):
    existing = set(db.scalars(select(RetailAlternative.product_key)))
    added = 0
    for values in ROWS:
        if values["product_key"] in existing:
            continue
        db.add(
            RetailAlternative(
                **values,
                observed_on=date(2026, 10, 18),
                notes="Alternativa de compra por rever, não uma certificação FODMAP deste produto "
                "ou porção. Confirmar rótulo, dose e restantes restrições. Preço observado, "
                "sem garantia de stock/preço na loja ou morada. Não altera a receita automaticamente.",
            )
        )
        added += 1
    key = "gluten-free-label-check"
    if db.scalar(select(FodmapReference).where(FodmapReference.reference_key == key)) is None:
        db.add(
            FodmapReference(
                reference_key=key,
                name_pt="Sem glúten: rever ingredientes",
                name_en="Gluten free: check ingredients",
                classification="variable",
                fodmap_groups=[],
                preparation="product label and serving must be checked",
                evidence_kind="public_educational_summary",
                source_name="Monash University",
                source_url="https://www.monashfodmap.com/about-fodmap-and-ibs/frequently-asked-questions/",
                source_version="public-faq-2026-10-18",
                retrieved_on=date(2026, 10, 18),
                notes_pt="Ingredientes à base de arroz/milho podem ser alternativas; o rótulo sem glúten não basta: produtos podem incluir cebola, pera ou mel. Confirmar composição e porção, sem extrapolar para a receita completa.",
                notes_en="Rice/corn based ingredients can be alternatives; gluten-free labeling is insufficient: products may include onion, pear or honey. Verify ingredients and portion without extrapolating to a complete meal.",
            )
        )
    db.commit()
    return added


if __name__ == "__main__":
    with SessionLocal() as session:
        print({"new_retail_products": import_retail_observations(session)})
