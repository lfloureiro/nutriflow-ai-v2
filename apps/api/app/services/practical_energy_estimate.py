from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from app.models.food_catalog import Recipe
from app.services.nutrition_learning import normalize_food_text
from app.services.recipe_structure_profile import (
    DIM_CARBOHYDRATE,
    DIM_ENERGY_MODIFIER,
    DIM_PROTEIN,
    IngredientStructure,
    build_recipe_structure_profile,
)
from app.services.recipe_units import QUALITATIVE_UNITS
from app.services.retail_quantity_estimates import PACKAGE_UNITS

_DEFAULT_SERVING_COUNT = Decimal(4)
_LIGHT_MEAL_DEFAULT_SERVING_COUNT = Decimal(1)
_ENERGY_QUANTUM = Decimal(1)
_PROTEIN_GRAMS_PER_SERVING = Decimal(180)
_FISH_GRAMS_PER_SERVING = Decimal(160)
_DRY_STAPLE_GRAMS_PER_SERVING = Decimal(80)
_POTATO_GRAMS_PER_SERVING = Decimal(250)
_QUALITATIVE_POTATO_GRAMS_PER_SERVING = Decimal(200)
_QUALITATIVE_DRY_STAPLE_GRAMS_PER_SERVING = Decimal(70)
_QUALITATIVE_LEGUME_GRAMS_PER_SERVING = Decimal(150)
_QUALITATIVE_PROTEIN_GRAMS_PER_SERVING = Decimal(150)


@dataclass(frozen=True)
class PracticalEnergyComponent:
    name: str
    energy_kcal: Decimal
    source: str
    confidence: str


@dataclass(frozen=True)
class PracticalEnergyEstimate:
    total_energy_kcal: Decimal
    serving_count: Decimal
    energy_per_serving_kcal: Decimal
    serving_count_source: str
    confidence: str
    driver_count: int
    covered_driver_count: int
    heuristic_driver_count: int
    components: tuple[PracticalEnergyComponent, ...]


def _q(value: Decimal) -> Decimal:
    return value.quantize(_ENERGY_QUANTUM, rounding=ROUND_HALF_UP)


def _normalized(name: str) -> str:
    return normalize_food_text(name)


def _contains(name: str, *roots: str) -> bool:
    normalized = _normalized(name)
    return any(root in normalized for root in roots)


def _is_fish(item: IngredientStructure) -> bool:
    return _contains(
        item.name,
        "bacalhau",
        "salmao",
        "pescad",
        "peixe",
        "perca",
        "atum",
        "sardinha",
        "polvo",
        "lula",
    )


def _is_dry_staple(item: IngredientStructure) -> bool:
    return _contains(
        item.name,
        "arroz",
        "massa",
        "macarronete",
        "esparguete",
        "fettuccine",
        "fetucine",
        "tagliatelle",
        "noodle",
        "cuscuz",
        "couscous",
        "quinoa",
    )


def _is_thickener(item: IngredientStructure) -> bool:
    return _contains(item.name, "farinha", "maisena", "amido")


def _is_legume(item: IngredientStructure) -> bool:
    return _contains(item.name, "grao", "feijao", "lentilha", "ervilha")


def _is_qualitative_structural_driver(item: IngredientStructure) -> bool:
    unit = item.unit.strip().casefold()
    if unit not in QUALITATIVE_UNITS:
        return False
    if DIM_PROTEIN in item.dimensions:
        return True
    return DIM_CARBOHYDRATE in item.dimensions and not _is_thickener(item)


def _ceil_ratio(quantity: Decimal, per_serving: Decimal) -> Decimal:
    return (quantity / per_serving).to_integral_value(rounding=ROUND_CEILING)


def _serving_hint(item: IngredientStructure) -> Decimal | None:
    unit = item.unit.strip().casefold()
    if unit in QUALITATIVE_UNITS:
        return None
    quantity = Decimal(item.quantity)

    if DIM_CARBOHYDRATE in item.dimensions and not _is_thickener(item):
        if unit == "g":
            if _is_dry_staple(item):
                return _ceil_ratio(quantity, _DRY_STAPLE_GRAMS_PER_SERVING)
            if _contains(item.name, "batata"):
                return _ceil_ratio(quantity, _POTATO_GRAMS_PER_SERVING)
        if unit == "kg":
            grams = quantity * Decimal(1000)
            if _is_dry_staple(item):
                return _ceil_ratio(grams, _DRY_STAPLE_GRAMS_PER_SERVING)
            if _contains(item.name, "batata"):
                return _ceil_ratio(grams, _POTATO_GRAMS_PER_SERVING)
        if unit in PACKAGE_UNITS and _is_dry_staple(item):
            return _ceil_ratio(
                quantity * Decimal(500),
                _DRY_STAPLE_GRAMS_PER_SERVING,
            )

    if DIM_PROTEIN in item.dimensions and unit in {"g", "kg"}:
        grams = quantity if unit == "g" else quantity * Decimal(1000)
        target = _FISH_GRAMS_PER_SERVING if _is_fish(item) else _PROTEIN_GRAMS_PER_SERVING
        return _ceil_ratio(grams, target)

    return None


def _default_serving_count(recipe: Recipe) -> Decimal:
    meal_types = set(recipe.suitable_meal_types or [])
    if meal_types and meal_types <= {"breakfast", "snack"}:
        return _LIGHT_MEAL_DEFAULT_SERVING_COUNT
    if recipe.source in {"development-breakfast", "development-snack"}:
        return _LIGHT_MEAL_DEFAULT_SERVING_COUNT
    return _DEFAULT_SERVING_COUNT


def _estimated_serving_count(recipe: Recipe, structure) -> tuple[Decimal, str]:
    default = _default_serving_count(recipe)
    hints = [
        hint
        for item in structure.ingredients
        if (hint := _serving_hint(item)) is not None and hint > 0
    ]
    if not hints:
        return default, "practical-default"
    max_hint = max(hints)
    if default == _LIGHT_MEAL_DEFAULT_SERVING_COUNT and max_hint <= default:
        return default, "practical-default"
    return max(default, max_hint), "practical-portion-inference"


def _density_kcal_per_g(item: IngredientStructure) -> Decimal | None:
    name = item.name
    if _contains(name, "azeite", "oleo"):
        return Decimal("8.84")
    if _contains(name, "margarina", "manteiga"):
        return Decimal("7.2")
    if _contains(name, "frutos secos", "amendoim", "amendoa", "caju", "avela", "pistach", "noz"):
        return Decimal("6.0")
    if _contains(name, "batata palha"):
        return Decimal("5.2")
    if _contains(name, "bacon", "chourico", "linguica", "alheira", "farinheira"):
        return Decimal("4.5")
    if _contains(name, "granola"):
        return Decimal("4.5")
    if _contains(name, "bolacha"):
        return Decimal("4.4")
    if _contains(name, "cere", "muesli", "cerelac", "nestum"):
        return Decimal("3.8")
    if _contains(name, "salsicha"):
        return Decimal("2.8")
    if _contains(name, "fiambre"):
        return Decimal("1.5")
    if _contains(name, "queijo"):
        return Decimal("4.0")
    if _contains(
        name,
        "arroz",
        "massa",
        "macarronete",
        "esparguete",
        "fettuccine",
        "fetucine",
        "farinha",
        "aveia",
    ):
        return Decimal("3.5")
    if _contains(name, "natas"):
        return Decimal("2.0")
    if _contains(name, "iogurte grego"):
        return Decimal("1.1")
    if _contains(name, "iogurt"):
        return Decimal("0.65")
    if _contains(name, "banana"):
        return Decimal("0.89")
    if _contains(name, "maca", "pera"):
        return Decimal("0.52")
    if _contains(name, "frutos vermelhos", "morango", "mirtil", "framboes"):
        return Decimal("0.50")
    if _contains(name, "laranja", "kiwi"):
        return Decimal("0.60")
    if _contains(name, "salmao"):
        return Decimal("2.1")
    if _contains(name, "entrecosto"):
        return Decimal("2.6")
    if _contains(name, "carne picada", "porco", "rojoes", "bifana"):
        return Decimal("2.0")
    if _contains(name, "vitela"):
        return Decimal("1.7")
    if _contains(name, "vaca", "carne"):
        return Decimal("1.9")
    if _contains(name, "almondeg", "hamburg"):
        return Decimal("2.2")
    if _contains(name, "peru", "frango", "coelho"):
        return Decimal("1.5")
    if _contains(name, "ovo"):
        return Decimal("1.45")
    if _contains(
        name,
        "bacalhau",
        "pescada",
        "peixe",
        "perca",
        "atum",
        "sardinha",
        "polvo",
        "lula",
    ):
        return Decimal("1.1")
    if _is_legume(item):
        return Decimal("1.2")
    if _contains(name, "batata"):
        return Decimal("0.8")
    if _contains(name, "leite"):
        return Decimal("0.5")
    if _contains(name, "pao"):
        return Decimal("2.6")
    if DIM_PROTEIN in item.dimensions:
        return Decimal("1.8")
    if DIM_CARBOHYDRATE in item.dimensions:
        return Decimal("2.5")
    if DIM_ENERGY_MODIFIER in item.dimensions:
        return Decimal("3.0")
    return None


def _density_kcal_per_ml(item: IngredientStructure) -> Decimal | None:
    name = item.name
    if _contains(name, "azeite", "oleo"):
        return Decimal("8.1")
    if _contains(name, "natas"):
        return Decimal("2.0")
    if _contains(name, "leite"):
        return Decimal("0.5")
    if _contains(name, "iogurt"):
        return Decimal("0.65")
    if DIM_ENERGY_MODIFIER in item.dimensions:
        return Decimal("1.0")
    return None


def _package_energy(item: IngredientStructure, quantity: Decimal) -> Decimal | None:
    name = item.name
    if _contains(name, "natas"):
        return quantity * Decimal(200) * Decimal("2.0")
    if _is_legume(item):
        return quantity * Decimal(240) * Decimal("1.2")
    if _contains(name, "cere", "muesli", "granola", "cerelac", "nestum"):
        return quantity * Decimal(375) * Decimal("3.8")
    if _contains(
        name,
        "massa",
        "macarronete",
        "esparguete",
        "arroz",
        "fettuccine",
        "fetucine",
    ):
        return quantity * Decimal(500) * Decimal("3.5")
    if _contains(name, "fiambre"):
        return quantity * Decimal(200) * Decimal("1.5")
    if _contains(name, "queijo"):
        return quantity * Decimal(200) * Decimal("4.0")
    if _contains(name, "iogurt"):
        return quantity * Decimal(125) * Decimal("0.65")
    if _contains(name, "frutos secos"):
        return quantity * Decimal(150) * Decimal("6.0")
    if DIM_CARBOHYDRATE in item.dimensions:
        return quantity * Decimal(400) * Decimal("2.5")
    if DIM_PROTEIN in item.dimensions:
        return quantity * Decimal(400) * Decimal("1.8")
    if DIM_ENERGY_MODIFIER in item.dimensions:
        return quantity * Decimal(200) * Decimal("3.0")
    return None


def _unit_energy(item: IngredientStructure, quantity: Decimal) -> Decimal | None:
    name = item.name
    if _contains(name, "ovo"):
        return quantity * Decimal(75)
    if _contains(name, "banana"):
        return quantity * Decimal(105)
    if _contains(name, "maca", "pera"):
        return quantity * Decimal(80)
    if _contains(name, "iogurt"):
        return quantity * Decimal(85)
    if _contains(name, "almondeg"):
        return quantity * Decimal(70)
    if _contains(name, "hamburg"):
        return quantity * Decimal(180)
    if _contains(name, "salsicha"):
        return quantity * Decimal(120)
    if _contains(name, "chourico", "linguica"):
        return quantity * Decimal(700)
    if _contains(name, "frango em pedacos"):
        return quantity * Decimal(1800)
    if _contains(name, "pescada fresca", "peixe para assar"):
        return quantity * Decimal(900)
    if _contains(name, "perca"):
        return quantity * Decimal(160)
    if _contains(name, "coelho"):
        return quantity * Decimal(1400)
    if DIM_PROTEIN in item.dimensions:
        return quantity * Decimal(150) * Decimal("1.8")
    if DIM_CARBOHYDRATE in item.dimensions:
        return quantity * Decimal(100) * Decimal("2.5")
    return None


def _heuristic_energy(item: IngredientStructure) -> Decimal | None:
    unit = item.unit.strip().casefold()
    if unit in QUALITATIVE_UNITS:
        return None
    quantity = Decimal(item.quantity)
    if unit == "g":
        density = _density_kcal_per_g(item)
        return quantity * density if density is not None else None
    if unit == "kg":
        density = _density_kcal_per_g(item)
        return quantity * Decimal(1000) * density if density is not None else None
    if unit == "ml":
        density = _density_kcal_per_ml(item)
        return quantity * density if density is not None else None
    if unit == "l":
        density = _density_kcal_per_ml(item)
        return quantity * Decimal(1000) * density if density is not None else None
    if unit in PACKAGE_UNITS:
        return _package_energy(item, quantity)
    if unit in {"un", "un.", "unid", "unidade", "unidades"}:
        return _unit_energy(item, quantity)
    return None


def _qualitative_structural_energy(
    item: IngredientStructure,
    serving_count: Decimal,
) -> Decimal | None:
    if not _is_qualitative_structural_driver(item):
        return None

    density = _density_kcal_per_g(item)
    if density is None:
        return None

    if DIM_CARBOHYDRATE in item.dimensions:
        if _contains(item.name, "batata"):
            grams_per_serving = _QUALITATIVE_POTATO_GRAMS_PER_SERVING
        elif _is_dry_staple(item):
            grams_per_serving = _QUALITATIVE_DRY_STAPLE_GRAMS_PER_SERVING
        elif _is_legume(item):
            grams_per_serving = _QUALITATIVE_LEGUME_GRAMS_PER_SERVING
        else:
            grams_per_serving = Decimal(150)
    else:
        grams_per_serving = _QUALITATIVE_PROTEIN_GRAMS_PER_SERVING

    return serving_count * grams_per_serving * density


def estimate_practical_recipe_energy(
    recipe: Recipe,
    *,
    known_energy_by_index: dict[int, Decimal] | None = None,
) -> PracticalEnergyEstimate | None:
    structure = build_recipe_structure_profile(recipe)
    if not structure.ingredients:
        return None

    if recipe.serving_count is not None:
        serving_count = recipe.serving_count
        serving_count_source = "catalogue"
    else:
        serving_count, serving_count_source = _estimated_serving_count(recipe, structure)

    known = known_energy_by_index or {}
    components: list[PracticalEnergyComponent] = []
    known_total = Decimal(0)
    heuristic_total = Decimal(0)
    driver_count = sum(
        item.major_calorie_driver or _is_qualitative_structural_driver(item)
        for item in structure.ingredients
    )
    covered_driver_count = 0
    heuristic_driver_count = 0

    for index, item in enumerate(structure.ingredients):
        known_energy = known.get(index)
        if known_energy is not None:
            known_total += known_energy
            components.append(
                PracticalEnergyComponent(
                    name=item.name,
                    energy_kcal=_q(known_energy),
                    source="catalogue",
                    confidence="high",
                )
            )
            if item.major_calorie_driver or _is_qualitative_structural_driver(item):
                covered_driver_count += 1
            continue

        if item.major_calorie_driver:
            heuristic = _heuristic_energy(item)
            source = "practical-heuristic"
        elif _is_qualitative_structural_driver(item):
            heuristic = _qualitative_structural_energy(item, serving_count)
            source = "practical-qualitative-default"
        else:
            continue

        if heuristic is None or heuristic <= 0:
            continue
        heuristic_total += heuristic
        covered_driver_count += 1
        heuristic_driver_count += 1
        components.append(
            PracticalEnergyComponent(
                name=item.name,
                energy_kcal=_q(heuristic),
                source=source,
                confidence="low",
            )
        )

    total = known_total + heuristic_total
    if total <= 0 or driver_count == 0 or covered_driver_count == 0:
        return None

    coverage = Decimal(covered_driver_count) / Decimal(driver_count)
    if coverage < Decimal("0.75"):
        return None

    per_serving = total / serving_count

    if covered_driver_count == driver_count and heuristic_driver_count == 0:
        confidence = "high"
    elif covered_driver_count == driver_count and heuristic_total <= known_total:
        confidence = "medium"
    else:
        confidence = "low"

    return PracticalEnergyEstimate(
        total_energy_kcal=_q(total),
        serving_count=serving_count,
        energy_per_serving_kcal=_q(per_serving),
        serving_count_source=serving_count_source,
        confidence=confidence,
        driver_count=driver_count,
        covered_driver_count=covered_driver_count,
        heuristic_driver_count=heuristic_driver_count,
        components=tuple(components),
    )


def practical_energy_payload(estimate: PracticalEnergyEstimate | None) -> dict[str, object] | None:
    if estimate is None:
        return None
    return {
        "total_energy_kcal": str(estimate.total_energy_kcal),
        "serving_count": str(estimate.serving_count),
        "energy_per_serving_kcal": str(estimate.energy_per_serving_kcal),
        "serving_count_source": estimate.serving_count_source,
        "confidence": estimate.confidence,
        "driver_count": estimate.driver_count,
        "covered_driver_count": estimate.covered_driver_count,
        "heuristic_driver_count": estimate.heuristic_driver_count,
        "components": [
            {
                "name": item.name,
                "energy_kcal": str(item.energy_kcal),
                "source": item.source,
                "confidence": item.confidence,
            }
            for item in estimate.components
        ],
    }
