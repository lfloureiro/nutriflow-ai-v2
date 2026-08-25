from decimal import Decimal

from app.services.nutrition_learning import RobustEnergyEstimate
from app.services.nutrition_learning_report import (
    STATUS_EVIDENCE_GOOD_SERVINGS_UNKNOWN,
    STATUS_GOOD,
    STATUS_LOW_EVIDENCE,
    STATUS_NO_EVIDENCE,
    STATUS_NO_INGREDIENTS,
    STATUS_QUANTITY_ANOMALY,
    STATUS_SEARCH_ERROR,
    NutritionLearningDiagnosticReport,
    RecipeLearningDiagnostic,
    classify_recipe_status,
)
from app.services.recipe_evidence_collector import RecipeEvidenceCollection


def _collection(*, confidence: str = "medium") -> RecipeEvidenceCollection:
    estimate = RobustEnergyEstimate(
        energy_kcal_per_serving=Decimal(491),
        lower_kcal_per_serving=Decimal(353),
        upper_kcal_per_serving=Decimal(501),
        evidence_count=3,
        retained_count=3,
        outlier_count=0,
        mean_similarity=Decimal("0.620"),
        confidence=confidence,
    )
    return RecipeEvidenceCollection(
        recipe_name="Bifes de peru com cogumelos",
        query="test",
        search_hit_count=9,
        structured_page_count=5,
        evidence=(),
        scored=(object(), object(), object()),  # type: ignore[arg-type]
        estimate=estimate,
        failed_page_count=0,
    )


def test_status_classification_keeps_quality_axes_conservative() -> None:
    medium = _collection(confidence="medium")
    low = _collection(confidence="low")

    assert (
        classify_recipe_status(
            ingredient_count=0,
            serving_count=None,
            anomaly_count=0,
            collection=None,
        )
        == STATUS_NO_INGREDIENTS
    )
    assert (
        classify_recipe_status(
            ingredient_count=5,
            serving_count=None,
            anomaly_count=0,
            collection=None,
            search_error="provider unavailable",
        )
        == STATUS_SEARCH_ERROR
    )
    assert (
        classify_recipe_status(
            ingredient_count=5,
            serving_count=None,
            anomaly_count=1,
            collection=medium,
        )
        == STATUS_QUANTITY_ANOMALY
    )
    assert (
        classify_recipe_status(
            ingredient_count=5,
            serving_count=None,
            anomaly_count=0,
            collection=None,
        )
        == STATUS_NO_EVIDENCE
    )
    assert (
        classify_recipe_status(
            ingredient_count=5,
            serving_count=None,
            anomaly_count=0,
            collection=low,
        )
        == STATUS_LOW_EVIDENCE
    )
    assert (
        classify_recipe_status(
            ingredient_count=5,
            serving_count=None,
            anomaly_count=0,
            collection=medium,
        )
        == STATUS_EVIDENCE_GOOD_SERVINGS_UNKNOWN
    )
    assert (
        classify_recipe_status(
            ingredient_count=5,
            serving_count=Decimal(4),
            anomaly_count=0,
            collection=medium,
        )
        == STATUS_GOOD
    )


def test_report_counts_statuses() -> None:
    base = {
        "recipe_name": "Recipe",
        "ingredient_count": 5,
        "serving_count": None,
        "search_hit_count": 0,
        "structured_page_count": 0,
        "failed_page_count": 0,
        "evidence_count": 0,
        "accepted_count": 0,
        "estimate_kcal_per_serving": None,
        "lower_kcal_per_serving": None,
        "upper_kcal_per_serving": None,
        "retained_source_count": 0,
        "mean_similarity": None,
        "confidence": None,
        "anomaly_count": 0,
        "anomalies": (),
        "error": None,
    }
    report = NutritionLearningDiagnosticReport(
        recipes=(
            RecipeLearningDiagnostic(**base, status=STATUS_NO_EVIDENCE),
            RecipeLearningDiagnostic(**base, status=STATUS_NO_EVIDENCE),
            RecipeLearningDiagnostic(**base, status=STATUS_LOW_EVIDENCE),
        )
    )

    assert report.status_counts == {
        STATUS_NO_EVIDENCE: 2,
        STATUS_LOW_EVIDENCE: 1,
    }
