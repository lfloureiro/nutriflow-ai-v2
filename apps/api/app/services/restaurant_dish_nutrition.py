import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from difflib import SequenceMatcher

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.food_catalog import Recipe, RecipeCompositionSnapshot
from app.schemas.external_menu import ExternalMenuNutrientWrite, ExternalMenuNutritionWrite
from app.services.recipe_nutrition import CALCULATION_VERSION
from app.services.restaurant_menu_scraper import ScrapedMenuItem

MIN_ESTIMATE_SCORE = Decimal("0.900")
MIN_ESTIMATE_MARGIN = Decimal("0.050")
STRUCTURAL_ESTIMATE_VERSION = "nutriflow-structural-dish-estimate-v1"


@dataclass(frozen=True)
class RestaurantDishNutritionEstimate:
    nutrition: ExternalMenuNutritionWrite
    recipe_key: str
    recipe_name: str
    score: Decimal


@dataclass(frozen=True)
class _DishEstimateValues:
    energy_kcal: Decimal
    protein_g: Decimal
    fiber_g: Decimal
    sodium_mg: Decimal
    confidence: Decimal
    signals: tuple[str, ...]


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def _similarity(item: ScrapedMenuItem, recipe: Recipe) -> Decimal:
    item_name = _normalize(item.name)
    recipe_name = _normalize(recipe.name)
    if item_name == recipe_name:
        return Decimal("0.980")
    name_score = Decimal(str(SequenceMatcher(None, item_name, recipe_name).ratio()))
    if item.description and recipe.description:
        description_score = Decimal(
            str(
                SequenceMatcher(
                    None,
                    _normalize(item.description),
                    _normalize(recipe.description),
                ).ratio()
            )
        )
        name_score = max(
            name_score,
            name_score * Decimal("0.8") + description_score * Decimal("0.2"),
        )
    return name_score.quantize(Decimal("0.001"))


def _trusted_composition(composition: RecipeCompositionSnapshot) -> bool:
    if composition.energy_kcal is None or composition.calculation_version != CALCULATION_VERSION:
        return False
    inputs = composition.calculation_inputs
    return not (isinstance(inputs, dict) and inputs.get("energy_estimated") is True)


def _latest_trusted_recipes(
    db: Session,
    family_id,
) -> list[tuple[Recipe, RecipeCompositionSnapshot]]:
    recipes = db.scalars(
        select(Recipe)
        .options(
            selectinload(Recipe.compositions).selectinload(RecipeCompositionSnapshot.nutrients)
        )
        .where(
            Recipe.is_active.is_(True),
            or_(Recipe.family_id.is_(None), Recipe.family_id == family_id),
        )
        .order_by(Recipe.name, Recipe.id)
    ).all()
    result: list[tuple[Recipe, RecipeCompositionSnapshot]] = []
    for recipe in recipes:
        trusted = [
            composition
            for composition in recipe.compositions
            if _trusted_composition(composition)
        ]
        if not trusted or recipe.serving_count is None or recipe.serving_count <= 0:
            continue
        result.append((recipe, trusted[-1]))
    return result


def _contains(text: str, *terms: str) -> bool:
    return any(term in text for term in terms)


def _structural_values(item: ScrapedMenuItem) -> _DishEstimateValues | None:
    text = _normalize(" ".join(part for part in (item.name, item.description) if part))
    if not text:
        return None

    if _contains(text, "sopa", "soup"):
        energy = Decimal(170)
        protein = Decimal(6)
        fiber = Decimal(2)
        sodium = Decimal(850)
        signals = ["soup"]
        if _contains(text, "milho", "corn"):
            energy += Decimal(35)
            fiber += Decimal(1)
            signals.append("corn")
        if _contains(text, "acida", "picante", "hot sour"):
            energy += Decimal(15)
            sodium += Decimal(150)
            signals.append("hot-sour")
        return _DishEstimateValues(
            energy,
            protein,
            fiber,
            sodium,
            Decimal("0.60"),
            tuple(signals),
        )

    if _contains(text, "hostia de camarao", "shrimp cracker", "prawn cracker"):
        return _DishEstimateValues(
            Decimal(220),
            Decimal(3),
            Decimal(1),
            Decimal(500),
            Decimal("0.58"),
            ("shrimp-crackers",),
        )

    if _contains(
        text,
        "crepe chines",
        "mini crepe",
        "spring roll",
        "rolo de primavera",
    ):
        energy = Decimal(220) if _contains(text, "mini crepe") else Decimal(190)
        return _DishEstimateValues(
            energy,
            Decimal(5),
            Decimal(2),
            Decimal(450),
            Decimal("0.58"),
            ("fried-appetizer",),
        )

    if _contains(text, "pizza"):
        return _DishEstimateValues(
            Decimal(820),
            Decimal(32),
            Decimal(5),
            Decimal(1650),
            Decimal("0.56"),
            ("pizza",),
        )

    if _contains(text, "hamburguer", "hamburger", "burger"):
        return _DishEstimateValues(
            Decimal(760),
            Decimal(35),
            Decimal(4),
            Decimal(1450),
            Decimal("0.56"),
            ("burger",),
        )

    if _contains(text, "sushi", "sashimi"):
        energy = Decimal(430) if "sushi" in text else Decimal(300)
        return _DishEstimateValues(
            energy,
            Decimal(24),
            Decimal(3),
            Decimal(950),
            Decimal("0.54"),
            ("sushi" if "sushi" in text else "sashimi",),
        )

    if _contains(text, "salada", "salad"):
        energy = Decimal(320)
        protein = Decimal(12)
        fiber = Decimal(7)
        sodium = Decimal(600)
        signals = ["salad"]
        if _contains(text, "queijo", "cheese", "feta", "parmesao", "parmesan"):
            energy += Decimal(140)
            protein += Decimal(8)
            sodium += Decimal(300)
            signals.append("cheese")
        if _contains(text, "noz", "amendoa", "nuts", "walnut"):
            energy += Decimal(120)
            protein += Decimal(3)
            fiber += Decimal(2)
            signals.append("nuts")
        return _DishEstimateValues(
            energy,
            protein,
            fiber,
            sodium,
            Decimal("0.55"),
            tuple(signals),
        )

    energy = Decimal(0)
    protein = Decimal(0)
    fiber = Decimal(0)
    sodium = Decimal(0)
    signals: list[str] = []

    carb_kind: str | None = None
    if _contains(text, "arroz chao chao", "fried rice"):
        carb_kind = "fried-rice"
        energy += Decimal(360)
        protein += Decimal(7)
        fiber += Decimal("2.5")
        sodium += Decimal(700)
    elif _contains(text, "chau min", "chao min", "chow mein", "mifan", "massa de arroz"):
        carb_kind = "noodles"
        energy += Decimal(350)
        protein += Decimal(8)
        fiber += Decimal(3)
        sodium += Decimal(600)
    elif _contains(
        text,
        "massa",
        "pasta",
        "spaghetti",
        "tagliatelle",
        "linguine",
        "penne",
    ):
        carb_kind = "pasta"
        energy += Decimal(430)
        protein += Decimal(14)
        fiber += Decimal(4)
        sodium += Decimal(250)
    elif _contains(text, "arroz", "rice"):
        carb_kind = "rice"
        energy += Decimal(280)
        protein += Decimal(5)
        fiber += Decimal(1)
        sodium += Decimal(100)
    elif _contains(text, "batata", "potato", "fries", "fritas"):
        carb_kind = "potato"
        energy += Decimal(360)
        protein += Decimal(6)
        fiber += Decimal(5)
        sodium += Decimal(500)

    if carb_kind:
        signals.append(carb_kind)

    protein_components: list[tuple[str, Decimal, Decimal, Decimal]] = []
    protein_definitions = (
        ("shrimp", ("gambas", "gamba", "camarao", "gamberetti"), 150, 28, 300),
        ("chicken", ("frango", "galinha", "chicken"), 190, 32, 160),
        ("beef", ("vaca", "beef"), 230, 29, 170),
        ("pork", ("porco", "pork"), 235, 28, 180),
        ("duck", ("pato", "duck"), 300, 24, 220),
        ("fish", ("peixe", "salmao", "atum", "bacalhau", "fish"), 200, 30, 180),
    )
    for label, terms, component_energy, component_protein, component_sodium in protein_definitions:
        if _contains(text, *terms):
            protein_components.append(
                (
                    label,
                    Decimal(component_energy),
                    Decimal(component_protein),
                    Decimal(component_sodium),
                )
            )

    if protein_components:
        if carb_kind:
            scale = Decimal("0.75") if len(protein_components) == 1 else Decimal("0.55")
            if len(protein_components) >= 3:
                scale = Decimal("0.45")
        else:
            scale = Decimal(1)
        for label, component_energy, component_protein, component_sodium in protein_components:
            energy += component_energy * scale
            protein += component_protein * scale
            sodium += component_sodium * scale
            signals.append(label)

    modifier_seen = False
    modifier_definitions = (
        ("carbonara", ("carbonara",), 320, 8, 1, 900),
        ("alfredo", ("alfredo",), 300, 6, 0, 700),
        ("pesto", ("pesto",), 260, 5, 2, 500),
        ("bolognese", ("bologna", "bolonhesa", "bolognese"), 240, 15, 3, 650),
        ("oyster-sauce", ("molho de ostras", "oyster sauce"), 100, 1, 0, 900),
        ("almonds", ("amendoa", "amendoas", "almond"), 130, 4, 2, 80),
        ("sweet-sour", ("doce e", "agridoce", "adocicada", "sweet sour"), 160, 1, 1, 400),
        ("pineapple", ("ananas", "pineapple"), 100, 0, 2, 80),
        ("chop-suey", ("chop suey",), 80, 2, 5, 450),
        ("cream-cheese", ("natas", "cream", "queijo", "cheese"), 220, 6, 0, 650),
        ("tomato-sauce", ("tomate", "tomato"), 120, 2, 3, 400),
    )
    for label, terms, add_energy, add_protein, add_fiber, add_sodium in modifier_definitions:
        if _contains(text, *terms):
            energy += Decimal(add_energy)
            protein += Decimal(add_protein)
            fiber += Decimal(add_fiber)
            sodium += Decimal(add_sodium)
            signals.append(label)
            modifier_seen = True

    if _contains(text, "frito", "frita", "fried") and carb_kind != "fried-rice":
        energy += Decimal(150)
        sodium += Decimal(180)
        signals.append("fried")
        modifier_seen = True

    if _contains(text, "picante", "spicy", "piri piri"):
        energy += Decimal(50)
        sodium += Decimal(250)
        signals.append("spicy-sauce")
        modifier_seen = True

    if carb_kind == "pasta" and not modifier_seen:
        energy += Decimal(160)
        sodium += Decimal(400)
        signals.append("generic-pasta-sauce")

    if _contains(text, "legumes", "vegetais", "vegetables") and "chop-suey" not in signals:
        energy += Decimal(60)
        fiber += Decimal(4)
        signals.append("vegetables")

    if not carb_kind and protein_components:
        energy += Decimal(170)
        fiber += Decimal(3)
        sodium += Decimal(350)
        signals.append("restaurant-cooking")

    if energy <= 0:
        return None

    signal_count = len(set(signals))
    confidence = Decimal("0.52")
    if carb_kind and protein_components:
        confidence = Decimal("0.64")
    elif carb_kind:
        confidence = Decimal("0.58")
    elif protein_components:
        confidence = Decimal("0.57")
    if modifier_seen:
        confidence += Decimal("0.03")
    if signal_count >= 4:
        confidence += Decimal("0.02")
    confidence = min(confidence, Decimal("0.72"))

    return _DishEstimateValues(
        energy.quantize(Decimal("1")),
        protein.quantize(Decimal("0.1")),
        fiber.quantize(Decimal("0.1")),
        sodium.quantize(Decimal("1")),
        confidence,
        tuple(dict.fromkeys(signals)),
    )


def estimate_structural_restaurant_dish_nutrition(
    item: ScrapedMenuItem,
) -> RestaurantDishNutritionEstimate | None:
    values = _structural_values(item)
    if values is None:
        return None
    basis_reference = (
        f"{STRUCTURAL_ESTIMATE_VERSION}:" + ",".join(values.signals)
    )[:255]
    nutrition = ExternalMenuNutritionWrite(
        evidence_level="estimated",
        confidence=values.confidence,
        basis_reference=basis_reference,
        reference_quantity=Decimal(1),
        reference_unit="serving",
        energy_kcal=values.energy_kcal,
        nutrients=[
            ExternalMenuNutrientWrite(key="protein", value=values.protein_g, unit="g"),
            ExternalMenuNutrientWrite(key="fiber", value=values.fiber_g, unit="g"),
            ExternalMenuNutrientWrite(key="sodium", value=values.sodium_mg, unit="mg"),
        ],
    )
    return RestaurantDishNutritionEstimate(
        nutrition=nutrition,
        recipe_key=STRUCTURAL_ESTIMATE_VERSION,
        recipe_name="Structural restaurant dish estimate",
        score=values.confidence,
    )


def estimate_restaurant_dish_nutrition(
    db: Session,
    *,
    family_id,
    item: ScrapedMenuItem,
) -> RestaurantDishNutritionEstimate | None:
    ranked = sorted(
        (
            (_similarity(item, recipe), recipe, composition)
            for recipe, composition in _latest_trusted_recipes(db, family_id)
        ),
        key=lambda value: (value[0], value[1].name.casefold()),
        reverse=True,
    )
    if ranked and ranked[0][0] >= MIN_ESTIMATE_SCORE:
        margin_ok = len(ranked) == 1 or ranked[0][0] - ranked[1][0] >= MIN_ESTIMATE_MARGIN
        if margin_ok:
            score, recipe, composition = ranked[0]
            serving_count = recipe.serving_count
            if serving_count is not None and serving_count > 0 and composition.energy_kcal is not None:
                basis_reference = f"nutriflow-recipe:{recipe.recipe_key}:{composition.id}"
                nutrition = ExternalMenuNutritionWrite(
                    evidence_level="estimated",
                    confidence=score,
                    basis_reference=basis_reference,
                    reference_quantity=Decimal(1),
                    reference_unit="serving",
                    energy_kcal=composition.energy_kcal / serving_count,
                    nutrients=[
                        ExternalMenuNutrientWrite(
                            key=nutrient.nutrient_key,
                            value=nutrient.value / serving_count,
                            unit=nutrient.unit,
                        )
                        for nutrient in composition.nutrients
                    ],
                )
                return RestaurantDishNutritionEstimate(
                    nutrition=nutrition,
                    recipe_key=recipe.recipe_key,
                    recipe_name=recipe.name,
                    score=score,
                )

    return estimate_structural_restaurant_dish_nutrition(item)
