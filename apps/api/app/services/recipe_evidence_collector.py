from dataclasses import dataclass
from decimal import Decimal

from app.services.nutrition_learning import (
    RecipeEvidence,
    RobustEnergyEstimate,
    ScoredRecipeEvidence,
    robust_recipe_energy_estimate,
    score_recipe_evidence,
)
from app.services.recipe_evidence_page import (
    RecipeEvidencePageError,
    fetch_structured_recipe_pages,
)
from app.services.recipe_evidence_search import (
    RecipeEvidenceSearchResult,
    search_recipe_nutrition_evidence,
)


@dataclass(frozen=True)
class RecipeEvidenceCollection:
    recipe_name: str
    query: str
    search_hit_count: int
    structured_page_count: int
    evidence: tuple[RecipeEvidence, ...]
    scored: tuple[ScoredRecipeEvidence, ...]
    estimate: RobustEnergyEstimate | None
    failed_page_count: int


def _snippet_evidence(
    search: RecipeEvidenceSearchResult,
) -> list[RecipeEvidence]:
    evidence: list[RecipeEvidence] = []
    for hit in search.hits:
        for mention in hit.calorie_mentions:
            if mention.basis != "per_serving":
                continue
            evidence.append(
                RecipeEvidence(
                    source="search-snippet",
                    source_reference=hit.url,
                    recipe_name=hit.title,
                    energy_kcal_per_serving=mention.energy_kcal,
                    source_quality=Decimal("0.45"),
                )
            )
    return evidence


def collect_recipe_nutrition_evidence(
    *,
    recipe_name: str,
    ingredient_names: tuple[str, ...] | list[str],
    max_results: int = 10,
) -> RecipeEvidenceCollection:
    search = search_recipe_nutrition_evidence(recipe_name, max_results=max_results)
    collected: list[RecipeEvidence] = []
    structured_page_count = 0
    failed_page_count = 0

    for hit in search.hits:
        try:
            pages = fetch_structured_recipe_pages(hit.url)
        except RecipeEvidencePageError:
            failed_page_count += 1
            continue
        structured_page_count += len(pages)
        for page in pages:
            item = page.as_recipe_evidence()
            if item is not None:
                collected.append(item)

    seen_references = {item.source_reference for item in collected}
    for item in _snippet_evidence(search):
        if item.source_reference in seen_references:
            continue
        collected.append(item)

    scored = score_recipe_evidence(
        recipe_name=recipe_name,
        ingredient_names=ingredient_names,
        evidence=collected,
    )
    estimate = robust_recipe_energy_estimate(scored)
    return RecipeEvidenceCollection(
        recipe_name=recipe_name,
        query=search.query,
        search_hit_count=len(search.hits),
        structured_page_count=structured_page_count,
        evidence=tuple(collected),
        scored=scored,
        estimate=estimate,
        failed_page_count=failed_page_count,
    )
