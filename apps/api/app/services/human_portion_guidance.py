from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from app.services.meal_recommendation import MealCandidate

QUANTITY_QUANTUM = Decimal("0.01")
QUALITATIVE_UNITS = frozenset({"qb", "q.b.", "q.b", "quanto baste"})


@dataclass(frozen=True)
class HumanPortionComponent:
    name: str
    quantity: Decimal | None
    unit: str
    qualitative: bool


@dataclass(frozen=True)
class HumanPortionGuidance:
    kind: Literal["recipe_components", "single_item"]
    components: tuple[HumanPortionComponent, ...]


def _q(value: Decimal) -> Decimal:
    return value.quantize(QUANTITY_QUANTUM, rounding=ROUND_HALF_UP)


def _recipe_components(candidate: MealCandidate) -> tuple[HumanPortionComponent, ...]:
    recipe = candidate.recipe
    composition = candidate.recipe_composition
    if recipe is None or composition is None or composition.reference_quantity <= 0:
        return ()

    fraction = candidate.quantity / composition.reference_quantity
    result: list[HumanPortionComponent] = []
    for ingredient in sorted(recipe.ingredients, key=lambda item: item.sort_order):
        unit = ingredient.unit.strip()
        qualitative = unit.casefold() in QUALITATIVE_UNITS
        result.append(
            HumanPortionComponent(
                name=ingredient.food_item.name,
                quantity=None if qualitative else _q(ingredient.quantity * fraction),
                unit=unit,
                qualitative=qualitative,
            )
        )
    return tuple(result)


def build_human_portion_guidance(
    candidate: MealCandidate,
) -> HumanPortionGuidance | None:
    if candidate.recipe is not None:
        components = _recipe_components(candidate)
        if not components:
            return None
        return HumanPortionGuidance(kind="recipe_components", components=components)

    if candidate.food_item is not None:
        return HumanPortionGuidance(
            kind="single_item",
            components=(
                HumanPortionComponent(
                    name=candidate.name,
                    quantity=_q(candidate.quantity),
                    unit=candidate.quantity_unit,
                    qualitative=False,
                ),
            ),
        )
    return None
