from decimal import Decimal

from app.services.recipe_evidence_page import (
    ingredient_name_from_line,
    parse_structured_recipe_pages,
)


def test_ingredient_name_from_line_removes_common_portuguese_measures() -> None:
    assert ingredient_name_from_line("400 g de bacalhau desfiado") == "bacalhau desfiado"
    assert ingredient_name_from_line("2 colheres de sopa de azeite") == "azeite"
    assert ingredient_name_from_line("1 lata de grão") == "grão"
    assert ingredient_name_from_line("4 ovos") == "ovos"


def test_parse_structured_recipe_page_reads_json_ld_recipe() -> None:
    html = """
    <html><head>
      <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": "Bacalhau com grão",
        "recipeYield": "4 porções",
        "recipeIngredient": [
          "400 g de bacalhau desfiado",
          "2 colheres de sopa de azeite",
          "1 lata de grão",
          "4 ovos"
        ],
        "nutrition": {"calories": "480 kcal"}
      }
      </script>
    </head></html>
    """

    pages = parse_structured_recipe_pages(
        html,
        source_reference="https://example.test/bacalhau",
    )

    assert len(pages) == 1
    page = pages[0]
    assert page.recipe_name == "Bacalhau com grão"
    assert page.energy_kcal_per_serving == Decimal(480)
    assert page.serving_count == Decimal(4)
    assert page.ingredient_names == (
        "bacalhau desfiado",
        "azeite",
        "grão",
        "ovos",
    )

    evidence = page.as_recipe_evidence()
    assert evidence is not None
    assert evidence.source == "example.test"
    assert evidence.total_energy_kcal == Decimal(1920)


def test_parse_structured_recipe_page_handles_graph_and_missing_nutrition() -> None:
    html = """
    <script type="application/ld+json">
    {
      "@graph": [
        {"@type": "WebPage", "name": "Page"},
        {
          "@type": ["Recipe", "Thing"],
          "name": "Arroz de bacalhau",
          "recipeYield": ["4 pessoas"],
          "recipeIngredient": ["250 g arroz", "400 g bacalhau"]
        }
      ]
    }
    </script>
    """

    pages = parse_structured_recipe_pages(
        html,
        source_reference="https://example.test/arroz",
    )

    assert len(pages) == 1
    assert pages[0].serving_count == Decimal(4)
    assert pages[0].energy_kcal_per_serving is None
    assert pages[0].as_recipe_evidence() is None
