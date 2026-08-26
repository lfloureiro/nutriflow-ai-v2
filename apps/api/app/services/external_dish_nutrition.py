import re
import unicodedata

from sqlalchemy.orm import Session

from app.schemas.external_menu import ExternalMenuNutritionWrite
from app.services.burgerking_nutrition import estimate_burgerking_nutrition
from app.services.kfc_nutrition import estimate_kfc_nutrition
from app.services.known_restaurant_nutrition import estimate_known_restaurant_nutrition
from app.services.mcdonalds_nutrition import estimate_mcdonalds_nutrition
from app.services.pronto_a_comer_nutrition import estimate_pronto_a_comer_nutrition
from app.services.restaurant_dish_nutrition import estimate_restaurant_dish_nutrition
from app.services.restaurant_menu_scraper import ScrapedMenuItem


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def is_non_meal_menu_item(
    name: str,
    *,
    description: str | None = None,
    merchant_name: str | None = None,
) -> bool:
    normalized = _normalize(name)
    combined = _normalize(" ".join(part for part in (name, description) if part))
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
        "guarana",
        "7up",
        "compal",
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
    if any(term in normalized for term in accessory_terms):
        return True

    dessert_terms = (
        "mcflurry",
        "gelado",
        "ice cream",
        "sundae",
    )
    if any(term in normalized for term in dessert_terms):
        return True

    # These are configurable bundles rather than fixed dishes. Their nutrition depends
    # on the selected drink, side, sauce, or child-menu configuration.
    configurable_bundle_terms = (
        "happy meal",
        "mcmenu",
        "share box",
    )
    if any(term in normalized for term in configurable_bundle_terms):
        return True

    merchant = _normalize(merchant_name or "")
    if "kfc" in merchant:
        if normalized.startswith("menu "):
            return True
        if normalized.startswith("box meal "):
            return True
        if "promocao" in normalized:
            return True
        # Normalization strips punctuation such as '+', so detect configurable
        # components by their words in the combined name/description text.
        if "bebida" in combined or "acompanhamento" in combined:
            return True
        if "molho dip" in normalized:
            return True
        # A fixed calorie total cannot be assigned safely because the chicken-part mix
        # is not specified by the marketplace item.
        if "pedacos" in normalized:
            return True
        # Sides and shakes may have nutrition, but they are not standalone meal
        # candidates in the current recommendation model.
        if any(
            term in normalized
            for term in (
                "shake ",
                "kentucky fries",
                "super batata",
                "batata grande",
            )
        ):
            return True

    if "burger king" in merchant:
        # Uber Eats menu bundles are configurable, so their total nutrition cannot be
        # represented as one fixed serving until the chosen burger, side and drink are
        # known.
        if normalized.startswith("menu "):
            return True
        if normalized.startswith("king jr "):
            return True
        if "a escolha" in combined or "acompanhamento" in combined:
            return True
        # These are sides/snacks rather than complete lunch/dinner candidates in the
        # current recommendation model.
        if any(
            term in normalized
            for term in (
                "chili cheese bites",
                "chicken fries",
                "king fries",
                "batata",
                "cheddar bombs",
                "nuggets",
            )
        ):
            return True

    if "pronto a comer de carnaxide" in merchant:
        # The marketplace mixes complete dishes with side dishes, soups, pastries,
        # desserts, breads, drinks and whole-family items. Keep only items that can be
        # ranked as one lunch/dinner candidate in the current planner.
        if normalized == "frango assado":
            return True
        if normalized.startswith("sopa ") or normalized == "canja de galinha":
            return True
        if normalized in {
            "arroz branco",
            "feijao verde salteado",
            "esparregado",
        }:
            return True
        if any(
            term in normalized
            for term in (
                "rissol",
                "chamuca",
                "croquete",
                "pastel de massa tenra",
                "pastel de bacalhau",
                "empada",
            )
        ):
            return True
        if normalized in {
            "arroz doce",
            "serradura",
            "pudim de ovos",
        }:
            return True
        if normalized in {
            "bola de agua",
            "palito",
            "bola de centeio",
            "pao com chourico",
            "pao de sementes",
        }:
            return True
        if normalized in {"pegoes branco", "mateus rose"}:
            return True

    return False


def resolve_external_dish_nutrition(
    db: Session,
    *,
    family_id,
    merchant_name: str | None,
    item: ScrapedMenuItem,
) -> ExternalMenuNutritionWrite | None:
    if is_non_meal_menu_item(
        item.name,
        description=item.description,
        merchant_name=merchant_name,
    ):
        return None

    mcdonalds = estimate_mcdonalds_nutrition(
        merchant_name=merchant_name,
        item=item,
    )
    if mcdonalds is not None:
        return mcdonalds

    kfc = estimate_kfc_nutrition(
        merchant_name=merchant_name,
        item=item,
    )
    if kfc is not None:
        return kfc

    burger_king = estimate_burgerking_nutrition(
        merchant_name=merchant_name,
        item=item,
    )
    if burger_king is not None:
        return burger_king

    pronto_a_comer = estimate_pronto_a_comer_nutrition(
        merchant_name=merchant_name,
        item=item,
    )
    if pronto_a_comer is not None:
        return pronto_a_comer

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
