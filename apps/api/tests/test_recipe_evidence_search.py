import json
from decimal import Decimal

from app.services import recipe_evidence_search


class _SecretStore:
    def get(self, name: str) -> str | None:
        if name == recipe_evidence_search.APIFY_API_TOKEN_SECRET:
            return "secret token"
        return None


def test_extract_calorie_mentions_distinguishes_serving_and_100g() -> None:
    mentions = recipe_evidence_search.extract_calorie_mentions(
        "Informação nutricional: 480 kcal por dose. Por 100 g: 178 kcal."
    )

    assert [(item.energy_kcal, item.basis) for item in mentions] == [
        (Decimal(480), "per_serving"),
        (Decimal(178), "per_100g"),
    ]


def test_recipe_search_name_removes_source_notes() -> None:
    assert (
        recipe_evidence_search.recipe_search_name(
            "Bacalhau com legumes (revista robot de cozinha)"
        )
        == "Bacalhau com legumes"
    )
    assert (
        recipe_evidence_search.recipe_search_name("Sopa [receita antiga]")
        == "Sopa"
    )


def test_search_recipe_nutrition_evidence_parses_apify_organic_results(
    monkeypatch,
) -> None:
    observed: dict[str, object] = {}

    def fake_request(url: str, *, data: bytes) -> object:
        observed["url"] = url
        observed["payload"] = json.loads(data.decode("utf-8"))
        return [
            {
                "organicResults": [
                    {
                        "position": 1,
                        "title": "Bacalhau com grão - 480 kcal por dose",
                        "url": "https://example.test/recipe",
                        "description": "Receita para quatro pessoas.",
                    },
                    {
                        "position": 2,
                        "title": "Informação nutricional",
                        "url": "https://example.test/second",
                        "description": "178 kcal por 100 g.",
                    },
                ]
            }
        ]

    monkeypatch.setattr(
        recipe_evidence_search,
        "get_provider_secret_store",
        lambda: _SecretStore(),
    )
    monkeypatch.setattr(recipe_evidence_search, "_request_json", fake_request)

    result = recipe_evidence_search.search_recipe_nutrition_evidence(
        "Bacalhau com grão",
        max_results=10,
    )

    assert result.query == '"Bacalhau com grão" receita'
    assert len(result.hits) == 2
    assert result.hits[0].calorie_mentions[0].energy_kcal == Decimal(480)
    assert result.hits[0].calorie_mentions[0].basis == "per_serving"
    assert result.hits[1].calorie_mentions[0].basis == "per_100g"
    assert "token=secret%20token" in str(observed["url"])
    payload = observed["payload"]
    assert isinstance(payload, dict)
    assert payload["queries"] == '"Bacalhau com grão" receita'
    assert payload["countryCode"] == "pt"
    assert payload["languageCode"] == "pt-PT"
    assert payload["maxPagesPerQuery"] == 1
    assert "resultsPerPage" not in payload
