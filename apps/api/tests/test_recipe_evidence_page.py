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
        "nutrition": {
          "calories": "480 kcal",
          "proteinContent": "38 g",
          "carbohydrateContent": "42 g",
          "fatContent": "18 g"
        }
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


def test_parse_structured_recipe_page_rejects_calories_inconsistent_with_macros() -> None:
    html = """
    <script type="application/ld+json">
    {
      "@type": "Recipe",
      "name": "Arroz de bacalhau",
      "recipeYield": "4 pessoas",
      "recipeIngredient": ["400 g bacalhau", "500 g arroz cozido"],
      "nutrition": {
        "calories": "45 kcal",
        "proteinContent": "3 g",
        "carbohydrateContent": "65 g",
        "fatContent": "1 g"
      }
    }
    </script>
    """

    pages = parse_structured_recipe_pages(
        html,
        source_reference="https://example.test/arroz",
    )

    assert len(pages) == 1
    assert pages[0].energy_kcal_per_serving is None
    assert pages[0].as_recipe_evidence() is None


def test_parse_structured_recipe_page_uses_visible_macros_as_sanity_check() -> None:
    html = """
    <html><body>
      <script type="application/ld+json">
      {
        "@type": "Recipe",
        "name": "Almôndegas fit",
        "recipeYield": "4 pessoas",
        "recipeIngredient": ["400 g carne moída", "1 cebola"],
        "nutrition": {"calories": "24 kcal"}
      }
      </script>
      <section>
        <h2>Valor nutricional</h2>
        <p>por pessoa</p>
        <p>Calorias: 24 kcal</p>
        <p>Proteínas: 2 g</p>
        <p>Gorduras: 16 g</p>
        <p>Carboidratos: 6 g</p>
      </section>
    </body></html>
    """

    pages = parse_structured_recipe_pages(
        html,
        source_reference="https://example.test/almondegas",
    )

    assert len(pages) == 1
    assert pages[0].energy_kcal_per_serving is None
    assert pages[0].as_recipe_evidence() is None


def test_parse_structured_recipe_page_rejects_probable_whole_recipe_nutrition() -> None:
    html = """
    <script type="application/ld+json">
    {
      "@type": "Recipe",
      "name": "Bifanas à moda do Porto",
      "recipeYield": "5 pessoas",
      "recipeIngredient": ["1500 g bifanas"],
      "nutrition": {
        "calories": "3451 kcal",
        "proteinContent": "352 g",
        "carbohydrateContent": "79 g",
        "fatContent": "108 g"
      }
    }
    </script>
    """

    pages = parse_structured_recipe_pages(
        html,
        source_reference="https://example.test/bifanas",
    )

    assert len(pages) == 1
    assert pages[0].serving_count == Decimal(5)
    assert pages[0].energy_kcal_per_serving is None


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
