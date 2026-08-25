from decimal import Decimal

from app.services.nutrition_learning import (
    IngredientQuantityObservation,
    RecipeEvidence,
    detect_quantity_anomalies,
    infer_single_unknown_energy,
    normalize_food_text,
    recipe_similarity,
    robust_recipe_energy_estimate,
    score_recipe_evidence,
)


def test_normalize_food_text_preserves_portuguese_food_words() -> None:
    assert normalize_food_text("Bacalhau com Grão-de-Bico") == "bacalhau com grao de bico"


def test_recipe_similarity_uses_name_and_ingredient_overlap() -> None:
    evidence = RecipeEvidence(
        source="test",
        source_reference="https://example.test/recipe",
        recipe_name="Bacalhau com grão",
        energy_kcal_per_serving=Decimal(480),
        ingredient_names=("bacalhau", "grão", "ovos", "azeite", "cebola"),
    )
    similar = recipe_similarity(
        recipe_name="Bacalhau com grão",
        ingredient_names=("bacalhau", "grão", "ovos", "azeite", "cebola", "salsa"),
        evidence=evidence,
    )
    unrelated = recipe_similarity(
        recipe_name="Mac and Cheese",
        ingredient_names=("massa", "cheddar", "leite"),
        evidence=evidence,
    )

    assert similar >= Decimal("0.80")
    assert unrelated < Decimal("0.30")


def test_robust_energy_estimate_discards_large_outlier() -> None:
    values = (350, 370, 390, 410, 420, 430, 450, 470, 500, 950)
    evidence = [
        RecipeEvidence(
            source=f"source-{index}",
            source_reference=f"https://example.test/{index}",
            recipe_name="Bacalhau com grão",
            energy_kcal_per_serving=Decimal(value),
        )
        for index, value in enumerate(values)
    ]
    scored = score_recipe_evidence(
        recipe_name="Bacalhau com grão",
        ingredient_names=(),
        evidence=evidence,
    )

    estimate = robust_recipe_energy_estimate(scored)

    assert estimate is not None
    assert estimate.energy_kcal_per_serving == Decimal(420)
    assert estimate.outlier_count == 1
    assert estimate.upper_kcal_per_serving == Decimal(500)
    assert estimate.confidence == "high"


def test_quantity_anomaly_flags_only_extreme_olive_oil_value() -> None:
    quantities = (30, 30, 30, 30, 50, 100, 300)
    observations = [
        IngredientQuantityObservation(
            recipe_name=f"recipe-{index}",
            catalog_key="legacy-v1:ingredient:12",
            ingredient_name="Azeite",
            quantity=Decimal(value),
            unit="ml",
        )
        for index, value in enumerate(quantities)
    ]

    anomalies = detect_quantity_anomalies(observations)

    assert len(anomalies) == 1
    assert anomalies[0].quantity == Decimal(300)
    assert anomalies[0].group_median == Decimal(30)
    assert anomalies[0].ratio_to_median == Decimal("10.00")


def test_single_unknown_inference_uses_recipe_energy_residual() -> None:
    inference = infer_single_unknown_energy(
        catalog_key="legacy-v1:ingredient:98",
        ingredient_name="Ovos",
        quantity=Decimal(4),
        unit="un",
        target_recipe_energy_kcal=Decimal(1000),
        known_ingredient_energy_kcal=Decimal(700),
    )

    assert inference is not None
    assert inference.inferred_contribution_kcal == Decimal(300)
    assert inference.inferred_kcal_per_unit == Decimal(75)
