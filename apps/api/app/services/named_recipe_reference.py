from dataclasses import dataclass
from decimal import Decimal

from app.services.nutrition_learning import normalize_food_text


@dataclass(frozen=True)
class NamedRecipeReference:
    energy_per_serving_kcal: Decimal
    confidence: str
    estimated: bool
    serving_description: str
    source_reference: str
    primary_protein: str | None
    primary_carbohydrate: str | None
    cooking_method: str
    energy_load_signal: str
    balance_signals: tuple[str, ...]
    suggested_accompaniments: tuple[str, ...]


def _normalized(value: str) -> str:
    return normalize_food_text(value)


def known_named_recipe_reference(recipe_name: str) -> NamedRecipeReference | None:
    """Return verified/practical references for ingredient-less legacy prepared foods.

    These references are deliberately narrow. They prevent a known branded/prepared food from
    becoming nutritionally invisible merely because the legacy catalogue stored only its name.
    Exact branded evidence is preferred; generic category estimates are explicitly low-confidence.
    """

    name = _normalized(recipe_name)

    if name == "douradinhos" or "douradinhos iglo" in name:
        return NamedRecipeReference(
            energy_per_serving_kcal=Decimal(184),
            confidence="high",
            estimated=False,
            serving_description="3 Douradinhos Iglo (aprox. 84 g)",
            source_reference=(
                "Iglo Portugal: Douradinhos de Peixe 15 un.; 218 kcal/100 g and "
                "184 kcal in the published portion table"
            ),
            primary_protein="Peixe branco panado (Douradinhos Iglo)",
            primary_carbohydrate="Panado",
            cooking_method="fried",
            energy_load_signal="moderate",
            balance_signals=("prepared_food",),
            suggested_accompaniments=("arroz", "legumes", "salada"),
        )

    if "rolo de carne" in name and "lidl" in name:
        return NamedRecipeReference(
            energy_per_serving_kcal=Decimal(260),
            confidence="low",
            estimated=True,
            serving_description="porção prática de rolo de carne (aprox. 150 g)",
            source_reference=(
                "Practical category estimate. Public references found for meatloaf are roughly "
                "153-175 kcal/100 g; exact Lidl variant was not uniquely identified."
            ),
            primary_protein="Rolo de carne",
            primary_carbohydrate=None,
            cooking_method="baked",
            energy_load_signal="moderate",
            balance_signals=("carb_light", "vegetables_missing"),
            suggested_accompaniments=("salada", "puré", "massa", "arroz"),
        )

    return None
