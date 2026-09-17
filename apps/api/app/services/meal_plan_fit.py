import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.daily_nutrition_state import DailyNutritionState
from app.models.food_adverse_reaction import FoodAdverseReaction
from app.models.person import Person
from app.schemas.meal_plan_fit import (
    MealPlanFitCandidateRead,
    MealPlanFitCreate,
    MealPlanFitGuidelineRead,
    MealPlanFitRead,
    MealPlanFitRuleRead,
)
from app.schemas.meal_recommendation import (
    RecommendationNutrientRead,
    RecommendationNutritionRead,
)
from app.schemas.nutrition_plan import (
    EffectiveNutritionNumericRuleRead,
    EffectiveNutritionPlanRead,
)
from app.services.meal_recommendation import MealCandidate
from app.services.meal_recommendation_api import (
    _load_candidates,
    _validate_candidate_meal_types,
)
from app.services.nutrition_plan import NutritionPlanError, compile_effective_nutrition_plan
from app.services.serving_nutrition import UnsupportedUnitConversionError, convert_quantity

ZERO = Decimal(0)
ONE = Decimal(1)
SCORE_QUANTUM = Decimal("0.0001")

_CANDIDATE_TARGET_TYPES = {
    "food",
    "food_item",
    "ingredient",
    "product",
    "dish",
    "beverage",
    "supplement",
    "generic",
    "recipe",
}
_MIN_OPERATORS = {"min", "gte", ">=", ">"}
_MAX_OPERATORS = {"max", "lte", "<=", "<"}


class MealPlanFitError(ValueError):
    pass


class MealPlanFitNotFoundError(MealPlanFitError):
    pass


def _active_on(start_date: date | None, end_date: date | None, on_date: date) -> bool:
    return (start_date is None or start_date <= on_date) and (
        end_date is None or on_date <= end_date
    )


def _load_person(db: Session, person_id: uuid.UUID) -> Person:
    person = db.get(
        Person,
        person_id,
        options=(selectinload(Person.food_adverse_reactions),),
    )
    if person is None:
        raise MealPlanFitNotFoundError("Person not found.")
    return person


def _load_daily_state(
    db: Session,
    *,
    person_id: uuid.UUID,
    planning_date: date,
    state_id: uuid.UUID | None,
) -> DailyNutritionState | None:
    options = (selectinload(DailyNutritionState.components),)
    if state_id is not None:
        state = db.get(DailyNutritionState, state_id, options=options)
        if state is None:
            raise MealPlanFitNotFoundError("DailyNutritionState not found.")
        if state.person_id != person_id:
            raise MealPlanFitError("DailyNutritionState belongs to a different Person.")
        if state.state_date != planning_date:
            raise MealPlanFitError(
                "DailyNutritionState state_date must match planning_date."
            )
        return state

    return db.scalar(
        select(DailyNutritionState)
        .where(
            DailyNutritionState.person_id == person_id,
            DailyNutritionState.state_date == planning_date,
        )
        .options(*options)
        .order_by(DailyNutritionState.computed_at.desc())
        .limit(1)
    )


def _candidate_matches(candidate: MealCandidate, target_type: str, target_key: str) -> bool:
    return (target_type, target_key) in candidate.subjects


def _candidate_value(
    candidate: MealCandidate,
    *,
    target_key: str,
    target_unit: str,
) -> Decimal | None:
    if target_key in {"energy", "energy_kcal", "calories"}:
        if candidate.nutrition.energy_kcal is None:
            return None
        return convert_quantity(candidate.nutrition.energy_kcal, "kcal", target_unit)

    nutrient = candidate.nutrition.nutrients.get(target_key)
    if nutrient is None:
        return None
    return convert_quantity(nutrient.value, nutrient.unit, target_unit)


def _daily_current_value(
    state: DailyNutritionState,
    *,
    target_key: str,
    target_unit: str,
) -> Decimal | None:
    if target_key in {"energy", "energy_kcal", "calories"}:
        total = (
            state.energy_consumed_kcal
            + state.energy_planned_kcal
            + state.energy_assumed_kcal
        )
        return convert_quantity(total, "kcal", target_unit)

    for component in state.components:
        if component.target_type != "nutrient" or component.target_key != target_key:
            continue
        total = (component.consumed_value or ZERO) + (component.planned_value or ZERO)
        return convert_quantity(total, component.unit, target_unit)
    return None


def _target_value(rule: EffectiveNutritionNumericRuleRead) -> Decimal | None:
    if rule.value_target is not None:
        return rule.value_target
    if (
        rule.operator == "target"
        and rule.value_min is not None
        and rule.value_max is not None
        and rule.value_min == rule.value_max
    ):
        return rule.value_min
    return None


def _score_min(observed: Decimal, target: Decimal) -> Decimal:
    if target <= ZERO:
        return ONE
    return min(ONE, max(ZERO, observed / target))


def _score_max(observed: Decimal, target: Decimal) -> Decimal:
    if observed <= target:
        return ONE
    if target <= ZERO:
        return ZERO
    excess = (observed - target) / target
    return max(ZERO, ONE - excess)


def _score_target(observed: Decimal, target: Decimal) -> Decimal:
    if target <= ZERO:
        return ONE if observed == target else ZERO
    distance = abs(observed - target) / target
    return max(ZERO, ONE - distance)


def _evaluate_numeric_value(
    rule: EffectiveNutritionNumericRuleRead,
    observed: Decimal,
) -> tuple[str, Decimal | None, str]:
    if rule.operator in _MIN_OPERATORS:
        if rule.value_min is None:
            return "unknown", None, "Minimum rule has no minimum value."
        score = _score_min(observed, rule.value_min)
        if observed >= rule.value_min:
            return "pass", score, "Candidate meets the minimum."
        return "fail", score, "Candidate is below the minimum."

    if rule.operator in _MAX_OPERATORS:
        if rule.value_max is None:
            return "unknown", None, "Maximum rule has no maximum value."
        score = _score_max(observed, rule.value_max)
        if observed <= rule.value_max:
            return "pass", score, "Candidate stays within the maximum."
        return "fail", score, "Candidate exceeds the maximum."

    if rule.operator == "range":
        if rule.value_min is None or rule.value_max is None:
            return "unknown", None, "Range rule requires both minimum and maximum values."
        if rule.value_min <= observed <= rule.value_max:
            return "pass", ONE, "Candidate is inside the target range."
        if observed < rule.value_min:
            return (
                "fail",
                _score_min(observed, rule.value_min),
                "Candidate is below the target range.",
            )
        return (
            "fail",
            _score_max(observed, rule.value_max),
            "Candidate is above the target range.",
        )

    if rule.operator == "target":
        target = _target_value(rule)
        if target is None:
            return "unknown", None, "Target rule has no usable target value."
        score = _score_target(observed, target)
        if observed == target:
            return "pass", score, "Candidate matches the target value."
        return "fail", score, "Candidate differs from the target value."

    return "unknown", None, f"Operator {rule.operator!r} is not supported by Plan-Fit v1."


def _rule_result(
    rule: EffectiveNutritionNumericRuleRead,
    *,
    scope: str,
    status: str,
    explanation: str,
    observed_value: Decimal | None = None,
    current_daily_value: Decimal | None = None,
    projected_daily_value: Decimal | None = None,
    score: Decimal | None = None,
) -> MealPlanFitRuleRead:
    return MealPlanFitRuleRead(
        rule_id=rule.id,
        target_type=rule.target_type,
        target_key=rule.target_key,
        operator=rule.operator,
        scope=scope,
        status=status,
        is_mandatory=rule.is_mandatory,
        priority=rule.priority,
        observed_value=observed_value,
        observed_unit=rule.unit if observed_value is not None else None,
        current_daily_value=current_daily_value,
        projected_daily_value=projected_daily_value,
        target_min=rule.value_min,
        target_max=rule.value_max,
        target_value=_target_value(rule),
        target_unit=rule.unit,
        score=(
            score.quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)
            if score is not None
            else None
        ),
        explanation=explanation,
        source=rule.source,
    )


def _evaluate_rule(
    rule: EffectiveNutritionNumericRuleRead,
    *,
    candidate: MealCandidate,
    daily_state: DailyNutritionState | None,
) -> MealPlanFitRuleRead:
    if rule.target_type in _CANDIDATE_TARGET_TYPES and rule.operator == "exclude":
        matched = _candidate_matches(candidate, rule.target_type, rule.target_key)
        return _rule_result(
            rule,
            scope="candidate",
            status="fail" if matched else "pass",
            score=ZERO if matched else ONE,
            explanation=(
                "Candidate contains an excluded food or recipe subject."
                if matched
                else "Candidate does not contain the excluded subject."
            ),
        )

    if rule.target_type != "nutrient":
        return _rule_result(
            rule,
            scope="meal" if rule.meal_type is not None else "daily",
            status="unknown",
            explanation=(
                f"Plan-Fit v1 cannot yet evaluate target type {rule.target_type!r} "
                "from composition evidence."
            ),
        )

    if rule.unit is None:
        return _rule_result(
            rule,
            scope="meal" if rule.meal_type is not None else "daily",
            status="unknown",
            explanation="The rule has no unit, so the candidate cannot be compared safely.",
        )

    try:
        candidate_value = _candidate_value(
            candidate,
            target_key=rule.target_key,
            target_unit=rule.unit,
        )
    except UnsupportedUnitConversionError:
        return _rule_result(
            rule,
            scope="meal" if rule.meal_type is not None else "daily",
            status="unknown",
            explanation="Candidate evidence uses a unit that cannot be converted safely.",
        )

    if candidate_value is None:
        return _rule_result(
            rule,
            scope="meal" if rule.meal_type is not None else "daily",
            status="unknown",
            explanation=f"Candidate has no evidence for {rule.target_key!r}.",
        )

    if rule.meal_type is not None:
        status, score, explanation = _evaluate_numeric_value(rule, candidate_value)
        return _rule_result(
            rule,
            scope="meal",
            status=status,
            score=score,
            observed_value=candidate_value,
            explanation=explanation,
        )

    if daily_state is None:
        return _rule_result(
            rule,
            scope="daily",
            status="unknown",
            observed_value=candidate_value,
            explanation="Daily rule requires DailyNutritionState context for this date.",
        )

    try:
        current = _daily_current_value(
            daily_state,
            target_key=rule.target_key,
            target_unit=rule.unit,
        )
    except UnsupportedUnitConversionError:
        return _rule_result(
            rule,
            scope="daily",
            status="unknown",
            observed_value=candidate_value,
            explanation="Daily state uses a unit that cannot be converted safely.",
        )

    if current is None:
        return _rule_result(
            rule,
            scope="daily",
            status="unknown",
            observed_value=candidate_value,
            explanation=f"Daily state has no tracked value for {rule.target_key!r}.",
        )

    projected = current + candidate_value
    status, score, explanation = _evaluate_numeric_value(rule, projected)

    if status == "fail" and rule.operator in _MIN_OPERATORS:
        status = "support"
        explanation = "Candidate moves the daily total toward the minimum but does not reach it yet."
        score = None
    elif status == "fail" and rule.operator == "range" and rule.value_min is not None:
        if projected < rule.value_min:
            status = "support"
            explanation = "Candidate moves the daily total toward the target range."
            score = None

    return _rule_result(
        rule,
        scope="daily",
        status=status,
        score=None if status == "support" else score,
        observed_value=candidate_value,
        current_daily_value=current,
        projected_daily_value=projected,
        explanation=explanation,
    )


def _mandatory_reaction_issues(
    reactions: list[FoodAdverseReaction],
    *,
    candidate: MealCandidate,
    planning_date: date,
) -> list[str]:
    issues: list[str] = []
    for reaction in reactions:
        if not reaction.is_mandatory:
            continue
        if not _active_on(reaction.start_date, reaction.end_date, planning_date):
            continue
        if _candidate_matches(candidate, reaction.subject_type, reaction.subject_key):
            issues.append(
                f"mandatory_reaction:{reaction.reaction_type}:"
                f"{reaction.subject_type}:{reaction.subject_key}"
            )
    return sorted(set(issues))


def _candidate_read(candidate: MealCandidate) -> MealPlanFitCandidateRead:
    return MealPlanFitCandidateRead(
        key=candidate.key,
        name=candidate.name,
        kind=candidate.kind,
        quantity=candidate.quantity,
        quantity_unit=candidate.quantity_unit,
        nutrition=RecommendationNutritionRead(
            energy_kcal=candidate.nutrition.energy_kcal,
            nutrients={
                key: RecommendationNutrientRead(value=value.value, unit=value.unit)
                for key, value in sorted(candidate.nutrition.nutrients.items())
            },
        ),
    )


def evaluate_meal_plan_fit(
    db: Session,
    *,
    person_id: uuid.UUID,
    data: MealPlanFitCreate,
) -> MealPlanFitRead:
    person = _load_person(db, person_id)
    daily_state = _load_daily_state(
        db,
        person_id=person.id,
        planning_date=data.planning_date,
        state_id=data.daily_nutrition_state_id,
    )

    candidates = _load_candidates(
        db,
        family_id=person.family_id,
        inputs=[data.candidate],
    )
    _validate_candidate_meal_types(
        db,
        family_id=person.family_id,
        meal_type=data.meal_type,
        candidates=candidates,
    )
    candidate = candidates[0]

    try:
        effective_plan: EffectiveNutritionPlanRead = compile_effective_nutrition_plan(
            db,
            person_id=person.id,
            on_date=data.planning_date,
            meal_type=data.meal_type,
        )
    except NutritionPlanError as exc:
        raise MealPlanFitError(str(exc)) from exc

    safety_issues = _mandatory_reaction_issues(
        list(person.food_adverse_reactions),
        candidate=candidate,
        planning_date=data.planning_date,
    )
    rule_results = [
        _evaluate_rule(rule, candidate=candidate, daily_state=daily_state)
        for rule in effective_plan.numeric_rules
    ]
    guideline_results = [
        MealPlanFitGuidelineRead(
            guideline_id=guideline.id,
            description=guideline.description,
            is_mandatory=guideline.is_mandatory,
            priority=guideline.priority,
            explanation=(
                "Weekly frequency progress is not evaluated in Plan-Fit v1."
                if guideline.guideline_type == "frequency"
                else "Qualitative guidance is preserved for explanation but is not scored in Plan-Fit v1."
            ),
            source=guideline.source,
        )
        for guideline in effective_plan.guidelines
    ]

    mandatory_conflict = any(
        conflict.severity == "mandatory" for conflict in effective_plan.conflicts
    )
    mandatory_fail = any(
        result.is_mandatory and result.status == "fail" for result in rule_results
    )
    mandatory_unknown = any(
        result.is_mandatory and result.status in {"unknown", "not_evaluated"}
        for result in rule_results
    ) or any(guideline.is_mandatory for guideline in guideline_results)

    scored = [
        result.score
        for result in rule_results
        if result.scope in {"candidate", "meal"} and result.score is not None
    ]
    fit_score = (
        (sum(scored, start=ZERO) / Decimal(len(scored))).quantize(
            SCORE_QUANTUM,
            rounding=ROUND_HALF_UP,
        )
        if scored
        else None
    )

    eligible = not (
        safety_issues or mandatory_conflict or mandatory_fail or mandatory_unknown
    )
    if mandatory_conflict:
        status = "conflict"
    elif safety_issues or mandatory_fail:
        status = "fail"
    elif mandatory_unknown or fit_score is None:
        status = "unknown"
    elif fit_score == ONE and not any(
        result.status in {"fail", "unknown"}
        for result in rule_results
        if result.scope in {"candidate", "meal"}
    ):
        status = "pass"
    else:
        status = "partial"

    explanation: list[str] = []
    if not effective_plan.active_plans:
        explanation.append(
            "No active NutritionPlan applies; standalone Person targets and constraints may still be shown."
        )
    if safety_issues:
        explanation.append("Candidate is blocked by a mandatory adverse-reaction rule.")
    if mandatory_conflict:
        explanation.append("The effective plan contains conflicting mandatory numeric guidance.")
    if mandatory_unknown:
        explanation.append(
            "At least one mandatory rule cannot be evaluated safely with the available evidence/context."
        )
    if fit_score is not None:
        explanation.append(
            "fit_score is the mean satisfaction score of candidate-level and meal-scoped numeric rules only."
        )
    if guideline_results:
        explanation.append(
            "Qualitative and weekly-frequency guidelines are displayed but not included in fit_score v1."
        )

    return MealPlanFitRead(
        person_id=person.id,
        planning_date=data.planning_date,
        meal_type=data.meal_type,
        daily_nutrition_state_id=daily_state.id if daily_state is not None else None,
        candidate=_candidate_read(candidate),
        eligible=eligible,
        status=status,
        fit_score=fit_score,
        active_plans=effective_plan.active_plans,
        conflicts=effective_plan.conflicts,
        safety_issues=safety_issues,
        rule_results=rule_results,
        guideline_results=guideline_results,
        explanation=explanation,
    )
