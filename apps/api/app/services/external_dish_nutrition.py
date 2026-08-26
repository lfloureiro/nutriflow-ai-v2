import re
import unicodedata

from sqlalchemy.orm import Session

from app.schemas.external_menu import ExternalMenuNutritionWrite
from app.services.known_restaurant_nutrition import estimate_known_restaurant_nutrition
from app.services.restaurant_dish_nutrition import estimate_restaurant_dish_nutrition
from app.services.restaurant_menu_scraper import ScrapedMenuItem


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def is_non_meal_menu_item(name: str) -> bool:
    normalized = _normalize(name)
    beverage_terms = (
        "agua",
        "limonada",
        "coca cola",
        "fanta",
        "sprite",
        "fuze tea",
        "ice tea",
        "iced tea",
        "pepsi",
        "sumo",
        "juice",
    )
    if any(term in normalized for term in beverage_terms):
        return True

    accessory_terms = (
        "talheres",
        "cutlery",
        "guardanapo",
        "napkin",
        "ingredientes extra",
        "molho extra",
        "extra carne",
        "extra queijo",
        "extra bacon",
    )
    return any(term in normalized for term in accessory_terms)


def resolve_external_dish_nutrition(
    db: Session,
    *,
    family_id,
    merchant_name: str | None,
    item: ScrapedMenuItem,
) -> ExternalMenuNutritionWrite | None:
    if is_non_meal_menu_item(item.name):
        return None

    known = estimate_known_restaurant_nutrition(
        merchant_name=merchant_name,
        item=item,
    )
    if known is not None:
        return known

    estimate = estimate_restaurant_dish_nutrition(
        db,
        family_id=family_id,
        item=item,
    )
    return None if estimate is None else estimate.nutrition
