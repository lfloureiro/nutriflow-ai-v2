from decimal import Decimal

from app.services.restaurant_menu_scraper import parse_html_menu


def test_json_ld_menu_items_preserve_price_and_official_calories() -> None:
    html = """
    <html><head>
      <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "Restaurant",
        "hasMenu": {
          "@type": "Menu",
          "hasMenuSection": [{
            "@type": "MenuSection",
            "hasMenuItem": [{
              "@type": "MenuItem",
              "name": "Frango grelhado com arroz",
              "description": "Frango, arroz e legumes",
              "offers": {"@type": "Offer", "price": "12.90", "priceCurrency": "EUR"},
              "nutrition": {"@type": "NutritionInformation", "calories": "610 kcal"}
            }]
          }]
        }
      }
      </script>
    </head></html>
    """

    items = parse_html_menu(html, source_url="https://example.test/menu")

    assert len(items) == 1
    assert items[0].name == "Frango grelhado com arroz"
    assert items[0].description == "Frango, arroz e legumes"
    assert items[0].price == Decimal("12.90")
    assert items[0].currency == "EUR"
    assert items[0].energy_kcal == Decimal(610)


def test_html_menu_blocks_extract_visible_dish_and_price() -> None:
    html = """
    <section class="menu">
      <article class="menu-item">
        <h3>Bife da vazia</h3>
        <p>Com arroz e legumes.</p>
        <span class="price">14,50 €</span>
      </article>
    </section>
    """

    items = parse_html_menu(html, source_url="https://example.test/ementa")

    assert len(items) == 1
    assert items[0].name == "Bife da vazia"
    assert items[0].description == "Com arroz e legumes."
    assert items[0].price == Decimal("14.50")
    assert items[0].energy_kcal is None


def test_duplicate_structured_and_html_item_is_collapsed() -> None:
    html = """
    <script type="application/ld+json">
      {"@type":"MenuItem","name":"Sopa do dia","offers":{"price":"3.50","priceCurrency":"EUR"}}
    </script>
    <article class="menu-item"><h3>Sopa do dia</h3><span class="price">3,50 €</span></article>
    """

    items = parse_html_menu(html, source_url="https://example.test/menu")

    assert len(items) == 1
