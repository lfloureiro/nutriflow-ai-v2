from decimal import Decimal

from app.models.food_catalog import FoodItem, Recipe, RecipeIngredient
from app.services.practical_energy_estimate import estimate_practical_recipe_energy


def _recipe(name: str, rows: list[tuple[str, Decimal, str]]) -> Recipe:
    recipe = Recipe(recipe_key=f"test:{name}", name=name, source="test")
    for index, (ingredient_name, quantity, unit) in enumerate(rows):
        food = FoodItem(
            catalog_key=f"test:{index}:{ingredient_name}",
            name=ingredient_name,
            food_kind="ingredient",
            source="test",
        )
        recipe.ingredients.append(
            RecipeIngredient(
                food_item=food,
                quantity=quantity,
                unit=unit,
                sort_order=index,
            )
        )
    return recipe


def test_estimate_focuses_on_main_calorie_drivers_and_defaults_to_four_servings() -> None:
    recipe = _recipe(
        "Arroz de bacalhau",
        [
            ("Bacalhau desfiado", Decimal(400), "g"),
            ("Arroz agulha", Decimal(280), "g"),
            ("Azeite", Decimal(30), "ml"),
            ("Cebola", Decimal(1), "un"),
            ("Pimenta preta", Decimal(1), "qb"),
        ],
    )

    estimate = estimate_practical_recipe_energy(recipe)

    assert estimate is not None
    assert estimate.serving_count == Decimal(4)
    assert estimate.serving_count_source == "practical-portion-inference"
    assert estimate.driver_count == 3
    assert estimate.covered_driver_count == 3
    assert estimate.total_energy_kcal > Decimal(1500)
    assert estimate.energy_per_serving_kcal > Decimal(350)


def test_known_catalogue_energy_is_preferred_to_heuristic_for_same_ingredient() -> None:
    recipe = _recipe(
        "Bifes de peru",
        [
            ("Bifes de peru", Decimal(800), "g"),
            ("Margarina", Decimal(100), "g"),
        ],
    )

    estimate = estimate_practical_recipe_energy(
        recipe,
        known_energy_by_index={0: Decimal(1000)},
    )

    assert estimate is not None
    turkey = next(item for item in estimate.components if item.name == "Bifes de peru")
    margarine = next(item for item in estimate.components if item.name == "Margarina")
    assert turkey.energy_kcal == Decimal(1000)
    assert turkey.source == "catalogue"
    assert margarine.source == "practical-heuristic"
    assert estimate.serving_count == Decimal(5)


def test_large_added_fat_is_reflected_in_numeric_energy_estimate() -> None:
    recipe = _recipe(
        "Bacalhau com grão",
        [
            ("Bacalhau desfiado", Decimal(400), "g"),
            ("Lata de grão", Decimal(2), "emb"),
            ("Ovos", Decimal(4), "un"),
            ("Azeite", Decimal(300), "ml"),
        ],
    )

    estimate = estimate_practical_recipe_energy(recipe)

    assert estimate is not None
    oil = next(item for item in estimate.components if item.name == "Azeite")
    assert oil.energy_kcal > Decimal(2000)
    assert estimate.energy_per_serving_kcal > Decimal(800)


def test_half_chicken_unit_is_treated_as_a_whole_animal_fraction() -> None:
    recipe = _recipe(
        "Frango com cebolinhas",
        [
            ("Frango em pedaços", Decimal("0.5"), "un"),
            ("Azeite", Decimal(30), "ml"),
        ],
    )

    estimate = estimate_practical_recipe_energy(recipe)

    assert estimate is not None
    chicken = next(item for item in estimate.components if item.name == "Frango em pedaços")
    assert chicken.energy_kcal == Decimal(900)
    assert estimate.energy_per_serving_kcal > Decimal(250)


def test_dry_pasta_package_infers_more_than_four_servings() -> None:
    recipe = _recipe(
        "Frango frito na actifry com fetucine",
        [
            ("Frango em pedaços", Decimal("0.5"), "un"),
            ("Fettuccine", Decimal(1), "emb"),
            ("Azeite", Decimal(30), "ml"),
        ],
    )

    estimate = estimate_practical_recipe_energy(recipe)

    assert estimate is not None
    assert estimate.serving_count == Decimal(7)
    assert estimate.serving_count_source == "practical-portion-inference"
    assert estimate.energy_per_serving_kcal > Decimal(350)


def test_piece_based_fish_and_sausages_receive_material_energy_estimates() -> None:
    fish = _recipe(
        "Perca do nilo no forno",
        [("Perca do nilo", Decimal(4), "un")],
    )
    sausages = _recipe(
        "Salsichas com couve lombarda",
        [("Salsichas frescas", Decimal(12), "un")],
    )

    fish_estimate = estimate_practical_recipe_energy(fish)
    sausage_estimate = estimate_practical_recipe_energy(sausages)

    assert fish_estimate is not None
    assert sausage_estimate is not None
    assert fish_estimate.total_energy_kcal == Decimal(640)
    assert sausage_estimate.total_energy_kcal == Decimal(1440)


def test_recipe_without_ingredients_does_not_invent_an_energy_value() -> None:
    recipe = Recipe(recipe_key="test:empty", name="Douradinhos", source="test")

    assert estimate_practical_recipe_energy(recipe) is None
