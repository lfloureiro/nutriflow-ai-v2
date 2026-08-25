from dataclasses import dataclass
from decimal import Decimal

from app.services.nutrition_learning import normalize_food_text
from app.services.recipe_evidence_search import (
    RecipeEvidenceSearchError,
    nutrition_web_evidence_configured,
    search_named_food_nutrition_evidence,
)


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


def _title_overlap(target: str, title: str) -> float:
    target_tokens = set(_normalized(target).split())
    title_tokens = set(_normalized(title).split())
    if not target_tokens:
        return 0.0
    return len(target_tokens & title_tokens) / len(target_tokens)


def _generic_web_reference(recipe_name: str) -> NamedRecipeReference | None:
    if not nutrition_web_evidence_configured():
        return None
    try:
        result = search_named_food_nutrition_evidence(recipe_name, max_results=5)
    except RecipeEvidenceSearchError:
        return None

    candidates: list[tuple[float, object, object]] = []
    for hit in result.hits:
        overlap = _title_overlap(recipe_name, hit.title)
        if overlap < 0.5:
            continue
        for mention in hit.calorie_mentions:
            if mention.basis not in {"per_serving", "per_100g"}:
                continue
            basis_bonus = 1.0 if mention.basis == "per_serving" else 0.5
            position_bonus = 0.2 if hit.position == 1 else 0.0
            candidates.append((overlap + basis_bonus + position_bonus, hit, mention))
    if not candidates:
        return None

    _, hit, mention = max(candidates, key=lambda item: item[0])
    energy = mention.energy_kcal
    if mention.basis == "per_100g":
        serving_description = "referência de 100 g"
    else:
        serving_description = "dose publicada pela fonte externa"

    normalized = _normalized(recipe_name)
    if any(root in normalized for root in ("carne", "frango", "peru", "peixe", "pesc", "salmao")):
        primary_protein: str | None = recipe_name
    else:
        primary_protein = None
    cooking_method = "baked" if any(root in normalized for root in ("rolo", "forno", "assad")) else "unknown"

    return NamedRecipeReference(
        energy_per_serving_kcal=energy,
        confidence="low",
        estimated=True,
        serving_description=serving_description,
        source_reference=hit.url,
        primary_protein=primary_protein,
        primary_carbohydrate=None,
        cooking_method=cooking_method,
        energy_load_signal="moderate",
        balance_signals=("external_named_food",),
        suggested_accompaniments=(),
    )


def resolve_named_recipe_reference(
    recipe_name: str,
    *,
    allow_web: bool = False,
) -> NamedRecipeReference | None:
    known = known_named_recipe_reference(recipe_name)
    if known is not None or not allow_web:
        return known
    return _generic_web_reference(recipe_name)
