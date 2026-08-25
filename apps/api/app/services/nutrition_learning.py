import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from difflib import SequenceMatcher
from statistics import median

QUALITATIVE_UNITS = frozenset({"qb", "q.b.", "q.b", "quanto baste"})
_MIN_EVIDENCE_SIMILARITY = Decimal("0.45")
_ANOMALY_MIN_GROUP_SIZE = 4
_ANOMALY_RATIO = Decimal(5)

_INGREDIENT_STOPWORDS = frozenset(
    {
        "a",
        "ao",
        "aos",
        "as",
        "com",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "e",
        "em",
        "para",
        "por",
        "quanto",
        "baste",
        "g",
        "gr",
        "kg",
        "mg",
        "ml",
        "cl",
        "l",
        "un",
        "unid",
        "unidade",
        "unidades",
        "c",
        "colher",
        "colheres",
        "sopa",
        "cha",
        "xicara",
        "xicaras",
        "copo",
        "copos",
        "emb",
        "embalagem",
        "lata",
        "latas",
        "fatia",
        "fatias",
        "dente",
        "dentes",
        "ramo",
        "ramos",
        "pitada",
        "pitadas",
        "gosto",
        "pequeno",
        "pequena",
        "pequenos",
        "pequenas",
        "medio",
        "media",
        "medios",
        "medias",
        "grande",
        "grandes",
        "fresco",
        "fresca",
        "frescos",
        "frescas",
        "seco",
        "seca",
        "secos",
        "secas",
        "cozido",
        "cozida",
        "cozidos",
        "cozidas",
        "cru",
        "crua",
        "crus",
        "cruas",
        "branco",
        "branca",
        "brancos",
        "brancas",
        "roxo",
        "roxa",
        "roxos",
        "roxas",
        "desfiado",
        "desfiada",
        "desfiados",
        "desfiadas",
        "lombo",
        "lombos",
        "virgem",
        "extra",
        "fino",
        "fina",
    }
)

_TOKEN_CANONICAL = {
    "cebolas": "cebola",
    "ovos": "ovo",
    "alhos": "alho",
    "tomates": "tomate",
    "cenouras": "cenoura",
    "batatas": "batata",
    "coentros": "coentro",
    "graos": "grao",
    "ervilhas": "ervilha",
    "pimentos": "pimento",
    "limoes": "limao",
}


@dataclass(frozen=True)
class RecipeEvidence:
    source: str
    source_reference: str
    recipe_name: str
    energy_kcal_per_serving: Decimal
    serving_count: Decimal | None = None
    ingredient_names: tuple[str, ...] = ()
    source_quality: Decimal = Decimal("0.75")

    @property
    def total_energy_kcal(self) -> Decimal | None:
        if self.serving_count is None:
            return None
        return self.energy_kcal_per_serving * self.serving_count


@dataclass(frozen=True)
class ScoredRecipeEvidence:
    evidence: RecipeEvidence
    similarity: Decimal

    @property
    def weight(self) -> Decimal:
        return max(Decimal(0), self.similarity) * max(
            Decimal(0),
            self.evidence.source_quality,
        )


@dataclass(frozen=True)
class RobustEnergyEstimate:
    energy_kcal_per_serving: Decimal
    lower_kcal_per_serving: Decimal
    upper_kcal_per_serving: Decimal
    evidence_count: int
    retained_count: int
    outlier_count: int
    mean_similarity: Decimal
    confidence: str


@dataclass(frozen=True)
class IngredientQuantityObservation:
    recipe_name: str
    catalog_key: str
    ingredient_name: str
    quantity: Decimal
    unit: str


@dataclass(frozen=True)
class IngredientQuantityAnomaly:
    recipe_name: str
    catalog_key: str
    ingredient_name: str
    quantity: Decimal
    unit: str
    group_median: Decimal
    ratio_to_median: Decimal


@dataclass(frozen=True)
class SingleUnknownEnergyInference:
    catalog_key: str
    ingredient_name: str
    unit: str
    quantity: Decimal
    inferred_contribution_kcal: Decimal
    inferred_kcal_per_unit: Decimal


def normalize_food_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def _name_similarity(target_name: str, candidate_name: str) -> Decimal:
    target_tokens = set(target_name.split())
    candidate_tokens = set(candidate_name.split())
    if target_tokens and target_tokens <= candidate_tokens:
        return Decimal(1)
    return Decimal(str(SequenceMatcher(None, target_name, candidate_name).ratio()))


def _ingredient_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for token in normalize_food_text(value).split():
        if token.isdigit() or token in _INGREDIENT_STOPWORDS:
            continue
        tokens.add(_TOKEN_CANONICAL.get(token, token))
    return tokens


def _ingredient_pair_similarity(left: str, right: str) -> Decimal:
    left_tokens = _ingredient_tokens(left)
    right_tokens = _ingredient_tokens(right)
    if not left_tokens or not right_tokens:
        return Decimal(0)
    intersection = left_tokens & right_tokens
    if not intersection:
        return Decimal(0)
    union = left_tokens | right_tokens
    jaccard = Decimal(len(intersection)) / Decimal(len(union))
    overlap = Decimal(len(intersection)) / Decimal(min(len(left_tokens), len(right_tokens)))
    return max(jaccard, overlap)


def _ingredient_set_similarity(
    target_values: tuple[str, ...] | list[str],
    evidence_values: tuple[str, ...] | list[str],
) -> Decimal:
    if not target_values or not evidence_values:
        return Decimal(0)

    candidates: list[tuple[Decimal, int, int]] = []
    for target_index, target in enumerate(target_values):
        for evidence_index, candidate in enumerate(evidence_values):
            similarity = _ingredient_pair_similarity(target, candidate)
            if similarity >= Decimal("0.50"):
                candidates.append((similarity, target_index, evidence_index))

    matched_target: set[int] = set()
    matched_evidence: set[int] = set()
    matched_weight = Decimal(0)
    for similarity, target_index, evidence_index in sorted(candidates, reverse=True):
        if target_index in matched_target or evidence_index in matched_evidence:
            continue
        matched_target.add(target_index)
        matched_evidence.add(evidence_index)
        matched_weight += similarity

    if not matched_target:
        return Decimal(0)

    target_coverage = matched_weight / Decimal(len(target_values))
    evidence_coverage = matched_weight / Decimal(len(evidence_values))
    if target_coverage + evidence_coverage == 0:
        return Decimal(0)
    return (
        Decimal(2)
        * target_coverage
        * evidence_coverage
        / (target_coverage + evidence_coverage)
    )


def recipe_similarity(
    *,
    recipe_name: str,
    ingredient_names: tuple[str, ...] | list[str],
    evidence: RecipeEvidence,
) -> Decimal:
    target_name = normalize_food_text(recipe_name)
    candidate_name = normalize_food_text(evidence.recipe_name)
    if not target_name or not candidate_name:
        return Decimal(0)

    name_score = _name_similarity(target_name, candidate_name)
    if not ingredient_names or not evidence.ingredient_names:
        return name_score.quantize(Decimal("0.001"))

    ingredient_score = _ingredient_set_similarity(
        ingredient_names,
        evidence.ingredient_names,
    )
    combined = (name_score * Decimal("0.40")) + (
        ingredient_score * Decimal("0.60")
    )
    return combined.quantize(Decimal("0.001"))


def score_recipe_evidence(
    *,
    recipe_name: str,
    ingredient_names: tuple[str, ...] | list[str],
    evidence: tuple[RecipeEvidence, ...] | list[RecipeEvidence],
    min_similarity: Decimal = _MIN_EVIDENCE_SIMILARITY,
) -> tuple[ScoredRecipeEvidence, ...]:
    scored = [
        ScoredRecipeEvidence(
            evidence=item,
            similarity=recipe_similarity(
                recipe_name=recipe_name,
                ingredient_names=ingredient_names,
                evidence=item,
            ),
        )
        for item in evidence
    ]
    return tuple(
        sorted(
            (item for item in scored if item.similarity >= min_similarity),
            key=lambda item: (item.similarity, item.evidence.source_quality),
            reverse=True,
        )
    )


def _weighted_median(values: list[tuple[Decimal, Decimal]]) -> Decimal:
    if not values:
        raise ValueError("Weighted median requires at least one value.")
    ordered = sorted(values, key=lambda item: item[0])
    total_weight = sum((max(weight, Decimal(0)) for _, weight in ordered), Decimal(0))
    if total_weight <= 0:
        return median([value for value, _ in ordered])
    threshold = total_weight / Decimal(2)
    cumulative = Decimal(0)
    for value, weight in ordered:
        cumulative += max(weight, Decimal(0))
        if cumulative >= threshold:
            return value
    return ordered[-1][0]


def _outlier_filtered(
    scored: tuple[ScoredRecipeEvidence, ...],
) -> tuple[ScoredRecipeEvidence, ...]:
    if len(scored) < 4:
        return scored

    values = [item.evidence.energy_kcal_per_serving for item in scored]
    center = median(values)
    deviations = [abs(value - center) for value in values]
    mad = median(deviations)
    if mad == 0:
        lower = center / Decimal(3)
        upper = center * Decimal(3)
        filtered = tuple(
            item
            for item in scored
            if lower <= item.evidence.energy_kcal_per_serving <= upper
        )
        return filtered or scored

    limit = mad * Decimal("4.5")
    filtered = tuple(
        item
        for item in scored
        if abs(item.evidence.energy_kcal_per_serving - center) <= limit
    )
    return filtered or scored


def _confidence(
    *,
    retained_count: int,
    center: Decimal,
    lower: Decimal,
    upper: Decimal,
    mean_similarity: Decimal,
) -> str:
    if center <= 0:
        return "low"
    relative_span = (upper - lower) / center
    if (
        retained_count >= 5
        and mean_similarity >= Decimal("0.70")
        and relative_span <= Decimal("0.40")
    ):
        return "high"
    if (
        retained_count >= 3
        and mean_similarity >= Decimal("0.55")
        and relative_span <= Decimal("0.80")
    ):
        return "medium"
    return "low"


def robust_recipe_energy_estimate(
    scored: tuple[ScoredRecipeEvidence, ...] | list[ScoredRecipeEvidence],
) -> RobustEnergyEstimate | None:
    candidates = tuple(
        item
        for item in scored
        if item.evidence.energy_kcal_per_serving > 0 and item.weight > 0
    )
    if not candidates:
        return None

    retained = _outlier_filtered(candidates)
    center = _weighted_median(
        [
            (item.evidence.energy_kcal_per_serving, item.weight)
            for item in retained
        ]
    )
    energies = sorted(item.evidence.energy_kcal_per_serving for item in retained)
    lower = energies[0]
    upper = energies[-1]
    total_weight = sum((item.weight for item in retained), Decimal(0))
    if total_weight > 0:
        mean_similarity = (
            sum((item.similarity * item.weight for item in retained), Decimal(0))
            / total_weight
        )
    else:
        mean_similarity = Decimal(0)

    return RobustEnergyEstimate(
        energy_kcal_per_serving=center,
        lower_kcal_per_serving=lower,
        upper_kcal_per_serving=upper,
        evidence_count=len(candidates),
        retained_count=len(retained),
        outlier_count=len(candidates) - len(retained),
        mean_similarity=mean_similarity.quantize(Decimal("0.001")),
        confidence=_confidence(
            retained_count=len(retained),
            center=center,
            lower=lower,
            upper=upper,
            mean_similarity=mean_similarity,
        ),
    )


def detect_quantity_anomalies(
    observations: tuple[IngredientQuantityObservation, ...]
    | list[IngredientQuantityObservation],
) -> tuple[IngredientQuantityAnomaly, ...]:
    groups: dict[tuple[str, str], list[IngredientQuantityObservation]] = {}
    for observation in observations:
        normalized_unit = observation.unit.strip().casefold()
        if normalized_unit in QUALITATIVE_UNITS or observation.quantity <= 0:
            continue
        groups.setdefault((observation.catalog_key, normalized_unit), []).append(
            observation
        )

    anomalies: list[IngredientQuantityAnomaly] = []
    for (_, normalized_unit), group in groups.items():
        if len(group) < _ANOMALY_MIN_GROUP_SIZE:
            continue
        group_median = median([item.quantity for item in group])
        if group_median <= 0:
            continue
        for item in group:
            ratio = item.quantity / group_median
            if ratio >= _ANOMALY_RATIO or ratio <= Decimal(1) / _ANOMALY_RATIO:
                anomalies.append(
                    IngredientQuantityAnomaly(
                        recipe_name=item.recipe_name,
                        catalog_key=item.catalog_key,
                        ingredient_name=item.ingredient_name,
                        quantity=item.quantity,
                        unit=normalized_unit,
                        group_median=group_median,
                        ratio_to_median=ratio.quantize(Decimal("0.01")),
                    )
                )

    return tuple(
        sorted(
            anomalies,
            key=lambda item: (
                abs(item.ratio_to_median - Decimal(1)),
                item.ingredient_name.casefold(),
                item.recipe_name.casefold(),
            ),
            reverse=True,
        )
    )


def infer_single_unknown_energy(
    *,
    catalog_key: str,
    ingredient_name: str,
    quantity: Decimal,
    unit: str,
    target_recipe_energy_kcal: Decimal,
    known_ingredient_energy_kcal: Decimal,
) -> SingleUnknownEnergyInference | None:
    if quantity <= 0 or target_recipe_energy_kcal <= 0:
        return None
    residual = target_recipe_energy_kcal - known_ingredient_energy_kcal
    if residual <= 0:
        return None
    return SingleUnknownEnergyInference(
        catalog_key=catalog_key,
        ingredient_name=ingredient_name,
        unit=unit.strip().casefold(),
        quantity=quantity,
        inferred_contribution_kcal=residual,
        inferred_kcal_per_unit=residual / quantity,
    )
