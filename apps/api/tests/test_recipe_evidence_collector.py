from decimal import Decimal

from app.services import recipe_evidence_collector
from app.services.recipe_evidence_page import StructuredRecipePage
from app.services.recipe_evidence_search import (
    CalorieMention,
    RecipeEvidenceSearchHit,
    RecipeEvidenceSearchResult,
)


def test_collect_recipe_nutrition_evidence_prefers_structured_pages(monkeypatch) -> None:
    search = RecipeEvidenceSearchResult(
        recipe_name="Bacalhau com grão",
        query='"Bacalhau com grão" calorias kcal receita',
        hits=(
            RecipeEvidenceSearchHit(
                title="Bacalhau com grão - 480 kcal por dose",
                url="https://example.test/a",
                description="Receita portuguesa",
                position=1,
                calorie_mentions=(
                    CalorieMention(
                        energy_kcal=Decimal(480),
                        basis="per_serving",
                        context="480 kcal por dose",
                    ),
                ),
            ),
            RecipeEvidenceSearchHit(
                title="Bacalhau com grão saudável",
                url="https://example.test/b",
                description="351 kcal por dose",
                position=2,
                calorie_mentions=(
                    CalorieMention(
                        energy_kcal=Decimal(351),
                        basis="per_serving",
                        context="351 kcal por dose",
                    ),
                ),
            ),
        ),
    )

    monkeypatch.setattr(
        recipe_evidence_collector,
        "search_recipe_nutrition_evidence",
        lambda recipe_name, max_results: search,
    )

    def fake_pages(url: str):
        if url.endswith("/a"):
            return (
                StructuredRecipePage(
                    source_reference=url,
                    recipe_name="Bacalhau com grão",
                    energy_kcal_per_serving=Decimal(480),
                    serving_count=Decimal(4),
                    ingredient_names=("bacalhau", "grão", "ovos", "azeite"),
                ),
            )
        return ()

    monkeypatch.setattr(
        recipe_evidence_collector,
        "fetch_structured_recipe_pages",
        fake_pages,
    )

    result = recipe_evidence_collector.collect_recipe_nutrition_evidence(
        recipe_name="Bacalhau com grão",
        ingredient_names=("Bacalhau desfiado", "Lata de grão", "Ovos", "Azeite"),
    )

    assert result.search_hit_count == 2
    assert result.structured_page_count == 1
    assert len(result.evidence) == 2
    assert result.evidence[0].source == "example.test"
    assert result.evidence[1].source == "search-snippet"
    assert result.estimate is not None
    assert result.estimate.energy_kcal_per_serving in {Decimal(351), Decimal(480)}


def test_collect_recipe_nutrition_evidence_tracks_failed_pages(monkeypatch) -> None:
    search = RecipeEvidenceSearchResult(
        recipe_name="Filetes no forno com limão",
        query="query",
        hits=(
            RecipeEvidenceSearchHit(
                title="Filetes no forno",
                url="https://example.test/fail",
                description=None,
                position=1,
                calorie_mentions=(),
            ),
        ),
    )
    monkeypatch.setattr(
        recipe_evidence_collector,
        "search_recipe_nutrition_evidence",
        lambda recipe_name, max_results: search,
    )

    def fail(_url: str):
        raise recipe_evidence_collector.RecipeEvidencePageError("blocked")

    monkeypatch.setattr(recipe_evidence_collector, "fetch_structured_recipe_pages", fail)

    result = recipe_evidence_collector.collect_recipe_nutrition_evidence(
        recipe_name="Filetes no forno com limão",
        ingredient_names=("Filetes de pescada", "Limão"),
    )

    assert result.failed_page_count == 1
    assert result.evidence == ()
    assert result.estimate is None
