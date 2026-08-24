import uuid
from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.food_catalog import FoodItem, Recipe, RecipeIngredient
from app.models.meal import MealEvent, MealParticipant, Serving
from app.models.meal_candidate_planning_profile import MealCandidatePlanningProfile
from app.schemas.practical_recommendation import RecommendationHistoryHint
from app.services.meal_recommendation import (
    CandidateEvaluation,
    MealCandidate,
    RecommendationResult,
)
from app.services.meal_suitability import (
    MealSuitabilityError,
    food_default_meal_types,
    recipe_default_meal_types,
    resolve_meal_types,
)
from app.services.shared_family_meal import (
    SharedFamilyMealRecommendationResult,
    SharedMealCandidateEvaluation,
    SharedMealParticipantEvaluation,
)

SCORE_QUANTUM = Decimal("0.0001")
ZERO = Decimal(0)
BALANCE_CATEGORIES = ("meat", "fish", "vegetarian_legumes")

RECIPE_USED_TODAY_PENALTY = Decimal("-3.5000")
RECIPE_USED_LAST_3_DAYS_PENALTY = Decimal("-3.0000")
RECIPE_USED_LAST_7_DAYS_PENALTY = Decimal("-2.0000")
RECIPE_USED_LAST_14_DAYS_PENALTY = Decimal("-1.0000")
RECIPE_USED_LAST_21_DAYS_PENALTY = Decimal("-0.4000")
NOVELTY_BONUS = Decimal("0.1500")
CATEGORY_BALANCE_BONUS = Decimal("0.4000")
CATEGORY_OVERUSE_PENALTY = Decimal("-0.3500")
SAME_PREVIOUS_CATEGORY_PENALTY = Decimal("-0.6000")
SAME_PREVIOUS_PROTEIN_PENALTY = Decimal("-0.4000")
CATEGORY_RECENT_REPEAT_PENALTY = Decimal("-0.5000")
THREE_MEATS_IN_A_ROW_PENALTY = Decimal("-0.8000")
PROTEIN_RECENT_REPEAT_PENALTY = Decimal("-0.4000")
MISSING_CATEGORY_PENALTY = Decimal("-0.1500")
LOOKBACK_DAYS = 28


class RecommendationDiversityError(ValueError):
    pass


class CandidatePlanningTraits:
    def __init__(
        self,
        *,
        category: str | None,
        primary_protein: str | None,
        suitable_meal_types: frozenset[str],
        auto_plan_enabled: bool,
    ) -> None:
        self.category = category
        self.primary_protein = primary_protein
        self.suitable_meal_types = suitable_meal_types
        self.auto_plan_enabled = auto_plan_enabled


class MealHistoryEntry:
    def __init__(
        self,
        *,
        plan_date: date,
        meal_type: str,
        candidate_key: str,
        category: str | None,
        primary_protein: str | None,
    ) -> None:
        self.plan_date = plan_date
        self.meal_type = meal_type
        self.candidate_key = candidate_key
        self.category = category
        self.primary_protein = primary_protein


def _normalize_token(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold().replace("-", "_").replace(" ", "_")
    return normalized or None


def _candidate_text(candidate: MealCandidate) -> str:
    values = [candidate.name]
    if candidate.recipe is not None:
        values.extend(ingredient.food_item.name for ingredient in candidate.recipe.ingredients)
    elif candidate.food_item is not None and candidate.food_item.description:
        values.append(candidate.food_item.description)
    return " ".join(values).casefold()


def _infer_category_and_protein(candidate: MealCandidate) -> tuple[str | None, str | None]:
    text = _candidate_text(candidate)

    fish_terms = {
        "salmão": "salmon",
        "salmao": "salmon",
        "bacalhau": "cod",
        "atum": "tuna",
        "pescada": "hake",
        "dourada": "fish",
        "robalo": "fish",
        "peixe": "fish",
    }
    for term, protein in fish_terms.items():
        if term in text:
            return "fish", protein

    meat_terms = {
        "frango": "chicken",
        "peru": "turkey",
        "vaca": "beef",
        "vitela": "beef",
        "porco": "pork",
        "carne picada": "beef",
        "almôndega": "beef",
        "almondega": "beef",
        "bolonhesa": "beef",
        "chili con carne": "beef",
    }
    for term, protein in meat_terms.items():
        if term in text:
            return "meat", protein

    vegetarian_terms = (
        "lentilha",
        "grão",
        "grao",
        "feijão",
        "feijao",
        "tofu",
        "vegetar",
    )
    if any(term in text for term in vegetarian_terms):
        return "vegetarian_legumes", "legumes"

    if "ovo" in text or "shakshuka" in text:
        return "eggs", "egg"
    return None, None


def _profile_identity(candidate: MealCandidate) -> tuple[str, uuid.UUID] | None:
    if candidate.food_item is not None and candidate.food_item.id is not None:
        return "food_item", candidate.food_item.id
    if candidate.recipe is not None and candidate.recipe.id is not None:
        return "recipe", candidate.recipe.id
    return None


def _profile_map(
    session: Session,
    *,
    family_id: uuid.UUID,
    candidates: list[MealCandidate],
) -> dict[tuple[str, uuid.UUID], MealCandidatePlanningProfile]:
    identities = [identity for candidate in candidates if (identity := _profile_identity(candidate))]
    food_ids = [identity for kind, identity in identities if kind == "food_item"]
    recipe_ids = [identity for kind, identity in identities if kind == "recipe"]
    filters = []
    if food_ids:
        filters.append(MealCandidatePlanningProfile.food_item_id.in_(food_ids))
    if recipe_ids:
        filters.append(MealCandidatePlanningProfile.recipe_id.in_(recipe_ids))
    if not filters:
        return {}

    rows = session.scalars(
        select(MealCandidatePlanningProfile).where(
            MealCandidatePlanningProfile.family_id == family_id,
            or_(*filters),
        )
    ).all()
    result: dict[tuple[str, uuid.UUID], MealCandidatePlanningProfile] = {}
    for row in rows:
        if row.food_item_id is not None:
            result[("food_item", row.food_item_id)] = row
        elif row.recipe_id is not None:
            result[("recipe", row.recipe_id)] = row
    return result


def _resolved_candidate_meal_types(
    candidate: MealCandidate,
    profile: MealCandidatePlanningProfile | None,
) -> frozenset[str]:
    if candidate.recipe is not None:
        catalogue = candidate.recipe.suitable_meal_types
        defaults = recipe_default_meal_types(candidate.recipe.source)
    elif candidate.food_item is not None:
        catalogue = candidate.food_item.suitable_meal_types
        defaults = food_default_meal_types(candidate.food_item.food_kind)
    else:
        raise RecommendationDiversityError(
            f"Candidate {candidate.key!r} has no catalogue entity."
        )
    try:
        return frozenset(
            resolve_meal_types(
                profile=profile,
                catalogue_meal_types=catalogue,
                defaults=defaults,
            )
        )
    except MealSuitabilityError as exc:
        raise RecommendationDiversityError(str(exc)) from exc


def _planning_traits(
    candidate: MealCandidate,
    profiles: dict[tuple[str, uuid.UUID], MealCandidatePlanningProfile],
) -> CandidatePlanningTraits:
    identity = _profile_identity(candidate)
    profile = profiles.get(identity) if identity is not None else None
    inferred_category, inferred_protein = _infer_category_and_protein(candidate)
    return CandidatePlanningTraits(
        category=(
            _normalize_token(profile.planning_category)
            if profile is not None and profile.planning_category
            else inferred_category
        ),
        primary_protein=(
            _normalize_token(profile.primary_protein)
            if profile is not None and profile.primary_protein
            else inferred_protein
        ),
        suitable_meal_types=_resolved_candidate_meal_types(candidate, profile),
        auto_plan_enabled=True if profile is None else profile.auto_plan_enabled,
    )


def _model_traits(model: FoodItem | Recipe) -> tuple[str | None, str | None]:
    name = model.name.casefold()
    if isinstance(model, Recipe):
        text = " ".join([name, *(ingredient.food_item.name.casefold() for ingredient in model.ingredients)])
    else:
        text = " ".join([name, (model.description or "").casefold()])

    pseudo_candidate = type("CandidateText", (), {"name": text, "recipe": None, "food_item": None})()
    fish_terms = ("salmão", "salmao", "bacalhau", "atum", "pescada", "peixe")
    if any(term in text for term in fish_terms):
        protein = "salmon" if "salm" in text else "tuna" if "atum" in text else "fish"
        return "fish", protein
    meat_terms = (
        ("frango", "chicken"),
        ("peru", "turkey"),
        ("vaca", "beef"),
        ("vitela", "beef"),
        ("porco", "pork"),
        ("bolonhesa", "beef"),
        ("carne", "beef"),
    )
    for term, protein in meat_terms:
        if term in text:
            return "meat", protein
    if any(term in text for term in ("lentilha", "grão", "grao", "feijão", "feijao", "vegetar")):
        return "vegetarian_legumes", "legumes"
    if "ovo" in text:
        return "eggs", "egg"
    del pseudo_candidate
    return None, None


def _event_local_date(event: MealEvent) -> date:
    try:
        return event.scheduled_at.astimezone(ZoneInfo(event.timezone)).date()
    except ZoneInfoNotFoundError:
        return event.scheduled_at.date()


def _event_candidate(event: MealEvent) -> tuple[str, str | None, str | None] | None:
    for participant in event.participants:
        for serving in participant.servings:
            if serving.recipe is not None:
                category, protein = _model_traits(serving.recipe)
                return serving.item_key or serving.recipe.recipe_key, category, protein
            if serving.food_item is not None:
                category, protein = _model_traits(serving.food_item)
                return serving.item_key or serving.food_item.catalog_key, category, protein
            if serving.item_key:
                return serving.item_key, None, None
    return None


def _actual_history(
    session: Session,
    *,
    family_id: uuid.UUID,
    planning_date: date,
) -> list[MealHistoryEntry]:
    start_date = planning_date - timedelta(days=LOOKBACK_DAYS)
    query_start = datetime.combine(start_date - timedelta(days=1), time.min, tzinfo=UTC)
    query_end = datetime.combine(planning_date + timedelta(days=2), time.min, tzinfo=UTC)
    events = session.scalars(
        select(MealEvent)
        .where(
            MealEvent.family_id == family_id,
            MealEvent.scheduled_at >= query_start,
            MealEvent.scheduled_at < query_end,
            MealEvent.status.in_(("planned", "prepared", "served", "completed")),
        )
        .options(
            selectinload(MealEvent.participants)
            .selectinload(MealParticipant.servings)
            .selectinload(Serving.recipe)
            .selectinload(Recipe.ingredients)
            .selectinload(RecipeIngredient.food_item),
            selectinload(MealEvent.participants)
            .selectinload(MealParticipant.servings)
            .selectinload(Serving.food_item),
        )
    ).all()

    result: list[MealHistoryEntry] = []
    for event in events:
        event_date = _event_local_date(event)
        if event_date < start_date or event_date > planning_date:
            continue
        identity = _event_candidate(event)
        if identity is None:
            continue
        candidate_key, category, protein = identity
        result.append(
            MealHistoryEntry(
                plan_date=event_date,
                meal_type=event.meal_type,
                candidate_key=candidate_key,
                category=category,
                primary_protein=protein,
            )
        )
    result.sort(key=lambda item: (item.plan_date, item.meal_type, item.candidate_key))
    return result


def _history_with_hints(
    session: Session,
    *,
    family_id: uuid.UUID,
    planning_date: date,
    meal_type: str,
    candidates: list[MealCandidate],
    profiles: dict[tuple[str, uuid.UUID], MealCandidatePlanningProfile],
    hints: list[RecommendationHistoryHint],
) -> list[MealHistoryEntry]:
    result = _actual_history(session, family_id=family_id, planning_date=planning_date)
    by_key = {candidate.key: candidate for candidate in candidates}
    for hint in hints:
        if hint.plan_date > planning_date:
            continue
        candidate = by_key.get(hint.candidate_key)
        if candidate is None:
            result.append(
                MealHistoryEntry(
                    plan_date=hint.plan_date,
                    meal_type=meal_type,
                    candidate_key=hint.candidate_key,
                    category=None,
                    primary_protein=None,
                )
            )
            continue
        traits = _planning_traits(candidate, profiles)
        result.append(
            MealHistoryEntry(
                plan_date=hint.plan_date,
                meal_type=meal_type,
                candidate_key=hint.candidate_key,
                category=traits.category,
                primary_protein=traits.primary_protein,
            )
        )
    result.sort(key=lambda item: (item.plan_date, item.meal_type, item.candidate_key))
    return result


def _diversity_score(
    *,
    candidate: MealCandidate,
    traits: CandidatePlanningTraits,
    planning_date: date,
    meal_type: str,
    history: list[MealHistoryEntry],
) -> tuple[Decimal, tuple[str, ...]]:
    score = ZERO
    reasons: list[str] = []

    previous_uses = [
        entry.plan_date
        for entry in history
        if entry.candidate_key == candidate.key and entry.plan_date <= planning_date
    ]
    if previous_uses:
        days_since = (planning_date - max(previous_uses)).days
        if days_since <= 0:
            score += RECIPE_USED_TODAY_PENALTY
            reasons.append("variety: already planned or used today")
        elif days_since <= 3:
            score += RECIPE_USED_LAST_3_DAYS_PENALTY
            reasons.append("variety: used in the last 3 days")
        elif days_since <= 7:
            score += RECIPE_USED_LAST_7_DAYS_PENALTY
            reasons.append("variety: used in the last 7 days")
        elif days_since <= 14:
            score += RECIPE_USED_LAST_14_DAYS_PENALTY
            reasons.append("variety: used in the last 14 days")
        elif days_since <= 21:
            score += RECIPE_USED_LAST_21_DAYS_PENALTY
            reasons.append("variety: used in the last 21 days")
    else:
        score += NOVELTY_BONUS
        reasons.append("variety: not used recently")

    prior = [entry for entry in history if entry.plan_date < planning_date]
    same_meal = [entry for entry in prior if entry.meal_type == meal_type]
    previous = same_meal[-1] if same_meal else (prior[-1] if prior else None)

    if traits.category is None:
        score += MISSING_CATEGORY_PENALTY
        reasons.append("variety: planning category is unknown")
    else:
        recent_week = [
            entry
            for entry in prior
            if entry.plan_date >= planning_date - timedelta(days=7)
            and entry.category in BALANCE_CATEGORIES
        ]
        if traits.category in BALANCE_CATEGORIES:
            counts = {category: 0 for category in BALANCE_CATEGORIES}
            for entry in recent_week:
                if entry.category in counts:
                    counts[entry.category] += 1
            minimum = min(counts.values())
            current = counts[traits.category]
            if current == minimum:
                score += CATEGORY_BALANCE_BONUS
                reasons.append("variety: improves meat/fish/vegetarian balance")
            elif current > minimum + 1:
                score += CATEGORY_OVERUSE_PENALTY
                reasons.append("variety: category is already overrepresented")

        if previous is not None and previous.category == traits.category:
            score += SAME_PREVIOUS_CATEGORY_PENALTY
            reasons.append("variety: avoids repeating the previous category")

        recent_categories = [
            entry.category
            for entry in same_meal[-3:]
            if entry.category is not None
        ]
        if recent_categories.count(traits.category) >= 2:
            score += CATEGORY_RECENT_REPEAT_PENALTY
            reasons.append("variety: category repeated too often recently")
        if traits.category == "meat" and len(recent_categories) >= 2 and all(
            category == "meat" for category in recent_categories[-2:]
        ):
            score += THREE_MEATS_IN_A_ROW_PENALTY
            reasons.append("variety: avoids three meat meals in a row")

    if traits.primary_protein is not None:
        if previous is not None and previous.primary_protein == traits.primary_protein:
            score += SAME_PREVIOUS_PROTEIN_PENALTY
            reasons.append("variety: avoids repeating the previous protein")
        recent_proteins = [
            entry.primary_protein
            for entry in same_meal[-4:]
            if entry.primary_protein is not None
        ]
        if recent_proteins.count(traits.primary_protein) >= 2:
            score += PROTEIN_RECENT_REPEAT_PENALTY
            reasons.append("variety: protein repeated too often recently")

    return score.quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP), tuple(reasons)


def _planning_exclusion(
    traits: CandidatePlanningTraits,
    meal_type: str,
) -> str | None:
    if not traits.auto_plan_enabled:
        return "planning_profile:auto_plan_disabled"
    if meal_type not in traits.suitable_meal_types:
        return f"planning_profile:not_suitable_for:{meal_type}"
    return None


def apply_diversity_to_recommendation(
    session: Session,
    *,
    family_id: uuid.UUID,
    planning_date: date,
    meal_type: str,
    recommendation: RecommendationResult,
    provisional_history: list[RecommendationHistoryHint],
) -> RecommendationResult:
    candidates = [evaluation.candidate for evaluation in recommendation.evaluations]
    profiles = _profile_map(session, family_id=family_id, candidates=candidates)
    history = _history_with_hints(
        session,
        family_id=family_id,
        planning_date=planning_date,
        meal_type=meal_type,
        candidates=candidates,
        profiles=profiles,
        hints=provisional_history,
    )

    adjusted: list[CandidateEvaluation] = []
    for evaluation in recommendation.evaluations:
        if not evaluation.eligible:
            adjusted.append(evaluation)
            continue
        traits = _planning_traits(evaluation.candidate, profiles)
        exclusion = _planning_exclusion(traits, meal_type)
        if exclusion is not None:
            adjusted.append(
                replace(
                    evaluation,
                    eligible=False,
                    rank=None,
                    score=None,
                    exclusion_reasons=tuple(sorted({*evaluation.exclusion_reasons, exclusion})),
                    explanation=evaluation.explanation + ("Excluded by meal-planning profile.",),
                )
            )
            continue

        diversity, reasons = _diversity_score(
            candidate=evaluation.candidate,
            traits=traits,
            planning_date=planning_date,
            meal_type=meal_type,
            history=history,
        )
        breakdown = dict(evaluation.score_breakdown)
        breakdown["diversity"] = diversity
        score = ((evaluation.score or ZERO) + diversity).quantize(
            SCORE_QUANTUM,
            rounding=ROUND_HALF_UP,
        )
        adjusted.append(
            replace(
                evaluation,
                rank=None,
                score=score,
                score_breakdown=breakdown,
                explanation=evaluation.explanation + reasons,
            )
        )

    eligible = sorted(
        (evaluation for evaluation in adjusted if evaluation.eligible),
        key=lambda evaluation: (-(evaluation.score or ZERO), evaluation.candidate.key),
    )
    ranks = {evaluation.candidate.key: index for index, evaluation in enumerate(eligible, 1)}
    ranked = [replace(item, rank=ranks.get(item.candidate.key)) for item in adjusted]
    ranked.sort(
        key=lambda evaluation: (
            0 if evaluation.eligible else 1,
            evaluation.rank if evaluation.rank is not None else 10**9,
            evaluation.candidate.key,
        )
    )
    return RecommendationResult(
        engine_version=f"{recommendation.engine_version}+diversity-v1",
        evaluations=tuple(ranked),
    )


def apply_diversity_to_shared_recommendation(
    session: Session,
    *,
    family_id: uuid.UUID,
    planning_date: date,
    meal_type: str,
    recommendation: SharedFamilyMealRecommendationResult,
    provisional_history: list[RecommendationHistoryHint],
) -> SharedFamilyMealRecommendationResult:
    candidates = [
        evaluation.participant_evaluations[0].evaluation.candidate
        for evaluation in recommendation.evaluations
        if evaluation.participant_evaluations
    ]
    profiles = _profile_map(session, family_id=family_id, candidates=candidates)
    history = _history_with_hints(
        session,
        family_id=family_id,
        planning_date=planning_date,
        meal_type=meal_type,
        candidates=candidates,
        profiles=profiles,
        hints=provisional_history,
    )

    adjusted: list[SharedMealCandidateEvaluation] = []
    for shared in recommendation.evaluations:
        if not shared.participant_evaluations or not shared.eligible:
            adjusted.append(shared)
            continue
        candidate = shared.participant_evaluations[0].evaluation.candidate
        traits = _planning_traits(candidate, profiles)
        exclusion = _planning_exclusion(traits, meal_type)
        if exclusion is not None:
            adjusted.append(
                replace(
                    shared,
                    eligible=False,
                    rank=None,
                    minimum_score=None,
                    average_score=None,
                    exclusion_reasons=tuple(sorted({*shared.exclusion_reasons, exclusion})),
                )
            )
            continue

        diversity, reasons = _diversity_score(
            candidate=candidate,
            traits=traits,
            planning_date=planning_date,
            meal_type=meal_type,
            history=history,
        )
        participant_evaluations: list[SharedMealParticipantEvaluation] = []
        for participant in shared.participant_evaluations:
            evaluation = participant.evaluation
            if not evaluation.eligible or evaluation.score is None:
                participant_evaluations.append(participant)
                continue
            breakdown = dict(evaluation.score_breakdown)
            breakdown["diversity"] = diversity
            participant_evaluations.append(
                replace(
                    participant,
                    evaluation=replace(
                        evaluation,
                        score=(evaluation.score + diversity).quantize(
                            SCORE_QUANTUM,
                            rounding=ROUND_HALF_UP,
                        ),
                        score_breakdown=breakdown,
                        explanation=evaluation.explanation + reasons,
                    ),
                )
            )

        minimum_score = (
            None
            if shared.minimum_score is None
            else (shared.minimum_score + diversity).quantize(
                SCORE_QUANTUM,
                rounding=ROUND_HALF_UP,
            )
        )
        average_score = (
            None
            if shared.average_score is None
            else (shared.average_score + diversity).quantize(
                SCORE_QUANTUM,
                rounding=ROUND_HALF_UP,
            )
        )
        adjusted.append(
            replace(
                shared,
                rank=None,
                minimum_score=minimum_score,
                average_score=average_score,
                participant_evaluations=tuple(participant_evaluations),
            )
        )

    eligible = sorted(
        (evaluation for evaluation in adjusted if evaluation.eligible),
        key=lambda evaluation: (
            -(evaluation.minimum_score or ZERO),
            -(evaluation.average_score or ZERO),
            evaluation.candidate_key,
        ),
    )
    ranks = {evaluation.candidate_key: index for index, evaluation in enumerate(eligible, 1)}
    ranked = [replace(item, rank=ranks.get(item.candidate_key)) for item in adjusted]
    ranked.sort(
        key=lambda evaluation: (
            0 if evaluation.eligible else 1,
            evaluation.rank if evaluation.rank is not None else 10**9,
            evaluation.candidate_key,
        )
    )
    return SharedFamilyMealRecommendationResult(
        engine_version=f"{recommendation.engine_version}+diversity-v1",
        evaluations=tuple(ranked),
    )
