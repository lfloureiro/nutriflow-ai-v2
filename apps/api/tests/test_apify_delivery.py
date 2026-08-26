from decimal import Decimal

from app.providers.apify_delivery import (
    _city_from_address,
    _glovo_rows,
    _merchant_matches,
    _uber_rows,
)
from app.providers.meal_delivery import MealDeliveryDiscoveryRequest


def _request(query: str | None = None) -> MealDeliveryDiscoveryRequest:
    return MealDeliveryDiscoveryRequest(
        delivery_address="Benfica, Lisboa",
        query=query,
        limit=20,
    )


def test_uber_rows_extracts_live_store_menu_items() -> None:
    rows = [
        {
            "uuid": "store-1",
            "title": "Li Yuan",
            "url": "https://www.ubereats.com/pt/store/li-yuan/example",
            "currencyCode": "EUR",
            "deliveryFeeTagline": "1,49 €",
            "menu": [
                {
                    "title": "Pratos",
                    "catalogItems": [
                        {
                            "uuid": "dish-1",
                            "title": "Vaca com Molho de Ostras e Arroz Chao Chao",
                            "itemDescription": "Vaca, legumes, molho de ostras e arroz.",
                            "price": 1240,
                            "priceTagline": "12,40 €",
                            "isSoldOut": False,
                        }
                    ],
                }
            ],
        }
    ]

    result = _uber_rows(rows, request=_request("Restaurante Li Yuan"))

    assert len(result) == 1
    item = result[0]
    assert item.provider_key == "uber_eats"
    assert item.provider_name == "Uber Eats"
    assert item.merchant_name == "Li Yuan"
    assert item.item_name == "Vaca com Molho de Ostras e Arroz Chao Chao"
    assert item.item_price == Decimal("12.40")
    assert item.delivery_fee == Decimal("1.49")
    assert item.currency == "EUR"
    assert item.location == "Benfica, Lisboa"
    assert item.source_kind == "delivery"
    assert item.source_reference.startswith("https://www.ubereats.com/")


def test_uber_rows_rejects_wrong_restaurant_returned_by_marketplace_search() -> None:
    rows = [
        {
            "uuid": "store-matuya",
            "title": "Matuya",
            "url": "https://www.ubereats.com/pt/store/matuya/example",
            "currencyCode": "EUR",
            "menu": [
                {
                    "title": "Pratos",
                    "catalogItems": [
                        {
                            "uuid": "dish-1",
                            "title": "Vaca com Molho Ostra",
                            "priceTagline": "10,00 €",
                        }
                    ],
                }
            ],
        }
    ]

    result = _uber_rows(rows, request=_request("Restaurante Li Yuan"))

    assert result == ()
    assert _merchant_matches("Restaurante Li Yuan", "Li Yuan")
    assert not _merchant_matches("Restaurante Li Yuan", "Matuya")


def test_uber_rows_deduplicates_same_catalog_item_across_sections() -> None:
    item = {
        "uuid": "dish-1",
        "title": "Carbonara",
        "priceTagline": "9,50 €",
    }
    rows = [
        {
            "uuid": "store-1",
            "title": "Tomatino",
            "url": "https://www.ubereats.com/pt/store/tomatino/example",
            "currencyCode": "EUR",
            "menu": [
                {"title": "Popular", "catalogItems": [item]},
                {"title": "Massas", "catalogItems": [item]},
            ],
        }
    ]

    result = _uber_rows(rows, request=_request("Tomatino"))

    assert len(result) == 1
    assert result[0].item_name == "Carbonara"


def test_uber_rows_prefers_nearest_matching_branch() -> None:
    rows = [
        {
            "uuid": "store-far",
            "title": "Tomatino (LoureShopping)",
            "url": "https://www.ubereats.com/pt/store/tomatino-loureshopping/example",
            "currencyCode": "EUR",
            "distance": {"text": "10,6 km"},
            "menu": [
                {
                    "title": "Massas",
                    "catalogItems": [
                        {
                            "uuid": "far-carbonara",
                            "title": "Carbonara",
                            "priceTagline": "9,50 €",
                        }
                    ],
                }
            ],
        },
        {
            "uuid": "store-near",
            "title": "Tomatino (Alegro Alfragide)",
            "url": "https://www.ubereats.com/pt/store/tomatino-alfragide/example",
            "currencyCode": "EUR",
            "distance": {
                "text": "2,4 km",
                "accessibilityText": "2,4\u00a0quilómetros",
            },
            "menu": [
                {
                    "title": "Massas",
                    "catalogItems": [
                        {
                            "uuid": "near-carbonara",
                            "title": "Carbonara",
                            "priceTagline": "9,50 €",
                        }
                    ],
                }
            ],
        },
    ]

    result = _uber_rows(rows, request=_request("Tomatino"))

    assert len(result) == 1
    assert result[0].merchant_name == "Tomatino (Alegro Alfragide)"
    assert result[0].item_key == "near-carbonara"


def test_glovo_rows_extracts_products_and_filters_by_query() -> None:
    rows = [
        {
            "recordType": "store",
            "slug": "tomatino-colombo",
            "name": "Tomatino",
            "url": "https://glovoapp.com/pt/pt/lisboa/stores/tomatino-colombo",
            "deliveryFeeEffective": "1,99 €",
        },
        {
            "recordType": "product",
            "storeSlug": "tomatino-colombo",
            "storeName": "Tomatino",
            "productId": "pasta-1",
            "name": "Bologna 200g",
            "description": "Massa com molho bolonhesa.",
            "price": "9.10",
            "currency": "EUR",
        },
        {
            "recordType": "product",
            "storeSlug": "other",
            "storeName": "Outro Restaurante",
            "productId": "other-1",
            "name": "Prato do dia",
            "price": "8.50",
            "currency": "EUR",
        },
    ]

    result = _glovo_rows(rows, request=_request("Tomatino"))

    assert len(result) == 1
    item = result[0]
    assert item.provider_key == "glovo"
    assert item.provider_name == "Glovo"
    assert item.merchant_name == "Tomatino"
    assert item.item_name == "Bologna 200g"
    assert item.item_price == Decimal("9.10")
    assert item.delivery_fee == Decimal("1.99")
    assert item.currency == "EUR"
    assert item.source_reference.startswith("https://glovoapp.com/")


def test_glovo_city_normalization_uses_lisbon_actor_city() -> None:
    assert _city_from_address("Benfica, Lisboa") == "Lisbon"
    assert _city_from_address("Rua Exemplo, Lisbon") == "Lisbon"
