import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.provider_secrets import get_provider_secret_store

FDC_API_BASE_URL = "https://api.nal.usda.gov/fdc/v1"
FDC_API_KEY_SECRET = "NUTRIFLOW_FDC_API_KEY"
FDC_TIMEOUT_SECONDS = 8.0
GENERIC_DATA_TYPES = ("Foundation", "SR Legacy")
_ENERGY_NUTRIENT_IDS = (1008, 2047, 2048)
_NUTRIENT_IDS = {
    "protein": 1003,
    "fat": 1004,
    "carbohydrate": 1005,
    "fiber": 1079,
    "sodium": 1093,
}


class FoodDataCentralError(ValueError):
    pass


@dataclass(frozen=True)
class FdcFoodSearchResult:
    fdc_id: int
    description: str
    data_type: str
    publication_date: str | None


@dataclass(frozen=True)
class FdcNutrient:
    key: str
    value: Decimal
    unit: str


@dataclass(frozen=True)
class FdcFoodPortion:
    portion_id: int
    amount: Decimal
    gram_weight: Decimal
    description: str
    measure_unit: str | None
    modifier: str | None

    @property
    def grams_per_measure_unit(self) -> Decimal:
        return self.gram_weight / self.amount


@dataclass(frozen=True)
class FdcFoodNutrition:
    fdc_id: int
    description: str
    data_type: str
    publication_date: str | None
    energy_kcal: Decimal | None
    nutrients: tuple[FdcNutrient, ...]
    portions: tuple[FdcFoodPortion, ...] = ()

    @property
    def source_reference(self) -> str:
        return f"https://fdc.nal.usda.gov/food-details/{self.fdc_id}/nutrients"


def _api_key() -> str:
    key = get_provider_secret_store().get(FDC_API_KEY_SECRET)
    if key is None:
        raise FoodDataCentralError(
            "FoodData Central requires NUTRIFLOW_FDC_API_KEY in the provider secret store."
        )
    return key


def _request_json(url: str, *, data: bytes | None = None) -> Any:
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urlopen(request, timeout=FDC_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise FoodDataCentralError("FoodData Central is unavailable.") from exc


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _positive_decimal(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _parse_search_response(payload: object) -> list[FdcFoodSearchResult]:
    if not isinstance(payload, dict):
        raise FoodDataCentralError("FoodData Central returned invalid search data.")
    foods = payload.get("foods")
    if not isinstance(foods, list):
        raise FoodDataCentralError("FoodData Central returned invalid search data.")

    results: list[FdcFoodSearchResult] = []
    for raw in foods:
        if not isinstance(raw, dict):
            continue
        fdc_id = _positive_int(raw.get("fdcId"))
        description = _optional_text(raw.get("description"))
        data_type = _optional_text(raw.get("dataType"))
        if fdc_id is None or description is None or data_type is None:
            continue
        results.append(
            FdcFoodSearchResult(
                fdc_id=fdc_id,
                description=description,
                data_type=data_type,
                publication_date=_optional_text(raw.get("publicationDate")),
            )
        )
    return results


def search_foods(
    query: str,
    *,
    limit: int = 10,
) -> list[FdcFoodSearchResult]:
    normalized = " ".join(query.strip().split())
    if not normalized:
        raise FoodDataCentralError("FoodData Central search requires a query.")
    page_size = min(max(limit, 1), 25)
    url = f"{FDC_API_BASE_URL}/foods/search?{urlencode({'api_key': _api_key()})}"
    payload = json.dumps(
        {
            "query": normalized,
            "dataType": list(GENERIC_DATA_TYPES),
            "pageSize": page_size,
            "pageNumber": 1,
        }
    ).encode("utf-8")
    return _parse_search_response(_request_json(url, data=payload))[:page_size]


def _canonical_unit(value: object) -> str | None:
    unit = _optional_text(value)
    if unit is None:
        return None
    normalized = unit.casefold()
    aliases = {
        "g": "g",
        "gram": "g",
        "grams": "g",
        "mg": "mg",
        "milligram": "mg",
        "milligrams": "mg",
        "kcal": "kcal",
    }
    return aliases.get(normalized)


def _nutrient_amounts(payload: dict[str, object]) -> dict[int, tuple[Decimal, str]]:
    raw_nutrients = payload.get("foodNutrients")
    if not isinstance(raw_nutrients, list):
        return {}

    values: dict[int, tuple[Decimal, str]] = {}
    for raw in raw_nutrients:
        if not isinstance(raw, dict):
            continue
        nutrient = raw.get("nutrient")
        if not isinstance(nutrient, dict):
            continue
        nutrient_id = _positive_int(nutrient.get("id"))
        unit = _canonical_unit(nutrient.get("unitName"))
        amount = raw.get("amount")
        if nutrient_id is None or unit is None or amount is None:
            continue
        try:
            parsed = Decimal(str(amount))
        except (InvalidOperation, TypeError, ValueError):
            continue
        if parsed < 0:
            continue
        values[nutrient_id] = (parsed, unit)
    return values


def _portion_measure_unit(raw: dict[str, object]) -> str | None:
    measure = raw.get("measureUnit")
    if isinstance(measure, dict):
        return (
            _optional_text(measure.get("abbreviation"))
            or _optional_text(measure.get("name"))
        )
    return _optional_text(measure)


def _parse_portions(payload: dict[str, object]) -> tuple[FdcFoodPortion, ...]:
    raw_portions = payload.get("foodPortions")
    if not isinstance(raw_portions, list):
        return ()

    portions: list[FdcFoodPortion] = []
    for raw in raw_portions:
        if not isinstance(raw, dict):
            continue
        portion_id = _positive_int(raw.get("id"))
        amount = _positive_decimal(raw.get("amount"))
        gram_weight = _positive_decimal(raw.get("gramWeight"))
        if portion_id is None or amount is None or gram_weight is None:
            continue
        modifier = _optional_text(raw.get("modifier"))
        measure_unit = _portion_measure_unit(raw)
        description = (
            _optional_text(raw.get("portionDescription"))
            or modifier
            or measure_unit
            or f"FDC portion {portion_id}"
        )
        portions.append(
            FdcFoodPortion(
                portion_id=portion_id,
                amount=amount,
                gram_weight=gram_weight,
                description=description,
                measure_unit=measure_unit,
                modifier=modifier,
            )
        )
    return tuple(portions)


def _parse_food_response(payload: object) -> FdcFoodNutrition:
    if not isinstance(payload, dict):
        raise FoodDataCentralError("FoodData Central returned invalid food data.")
    fdc_id = _positive_int(payload.get("fdcId"))
    description = _optional_text(payload.get("description"))
    data_type = _optional_text(payload.get("dataType"))
    if fdc_id is None or description is None or data_type is None:
        raise FoodDataCentralError("FoodData Central returned incomplete food data.")

    amounts = _nutrient_amounts(payload)
    energy_kcal: Decimal | None = None
    for nutrient_id in _ENERGY_NUTRIENT_IDS:
        nutrient = amounts.get(nutrient_id)
        if nutrient is not None and nutrient[1] == "kcal":
            energy_kcal = nutrient[0]
            break

    nutrients: list[FdcNutrient] = []
    for key, nutrient_id in _NUTRIENT_IDS.items():
        nutrient = amounts.get(nutrient_id)
        if nutrient is None:
            continue
        value, unit = nutrient
        nutrients.append(FdcNutrient(key=key, value=value, unit=unit))

    return FdcFoodNutrition(
        fdc_id=fdc_id,
        description=description,
        data_type=data_type,
        publication_date=_optional_text(payload.get("publicationDate")),
        energy_kcal=energy_kcal,
        nutrients=tuple(nutrients),
        portions=_parse_portions(payload),
    )


def fetch_food_nutrition(fdc_id: int) -> FdcFoodNutrition:
    if fdc_id <= 0:
        raise FoodDataCentralError("fdc_id must be positive.")
    url = f"{FDC_API_BASE_URL}/food/{fdc_id}?{urlencode({'api_key': _api_key()})}"
    return _parse_food_response(_request_json(url))
