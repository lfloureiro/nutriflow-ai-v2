import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.nutrition_constraint import NutritionConstraint
from app.models.nutrition_goal import NutritionGoal
from app.models.nutrition_plan import NutritionPlan, NutritionPlanGuideline, NutritionPlanRule
from app.models.nutrition_target import NutritionTarget, NutritionTargetComponent
from app.models.person import Person
from app.schemas.meal_type import MealType
from app.schemas.nutrition_plan import (
    EffectiveNutritionGoalRead,
    EffectiveNutritionGuidelineRead,
    EffectiveNutritionNumericRuleRead,
    EffectiveNutritionPlanConflictRead,
    EffectiveNutritionPlanRead,
    EffectiveNutritionPlanSourceRead,
    NutritionPlanCreate,
    NutritionPlanGuidelineCreate,
    NutritionPlanGuidelineUpdate,
    NutritionPlanRuleCreate,
    NutritionPlanUpdate,
    NutritionPlanVersionCreate,
)


class NutritionPlanError(ValueError):
    pass


_SOURCE_PRIORITY = {
    "clinician": 500,
    "nutritionist": 500,
    "user": 300,
    "imported": 250,
    "system": 100,
}

_ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"active", "inactive"},
    "active": {"inactive", "superseded"},
    "inactive": {"active", "superseded"},
    "superseded": set(),
}


def _source_priority(source: str | None) -> int:
    return _SOURCE_PRIORITY.get(source or "", 0)


def _plan_query(person_id: uuid.UUID):
    return (
        select(NutritionPlan)
        .where(NutritionPlan.person_id == person_id)
        .options(
            selectinload(NutritionPlan.rules).selectinload(NutritionPlanRule.nutrition_constraint),
            selectinload(NutritionPlan.rules)
            .selectinload(NutritionPlanRule.nutrition_target_component)
            .selectinload(NutritionTargetComponent.nutrition_target),
            selectinload(NutritionPlan.rules).selectinload(NutritionPlanRule.nutrition_goal),
            selectinload(NutritionPlan.guidelines),
        )
    )


def get_nutrition_plan(
    db: Session,
    *,
    person_id: uuid.UUID,
    plan_id: uuid.UUID,
) -> NutritionPlan | None:
    return db.scalar(_plan_query(person_id).where(NutritionPlan.id == plan_id))


def list_nutrition_plans(db: Session, *, person_id: uuid.UUID) -> list[NutritionPlan]:
    return list(
        db.scalars(
            _plan_query(person_id).order_by(
                NutritionPlan.lineage_id,
                NutritionPlan.version.desc(),
            )
        ).all()
    )


def _activate_plan_lineage(db: Session, plan: NutritionPlan) -> None:
    other_active = db.scalars(
        select(NutritionPlan).where(
            NutritionPlan.person_id == plan.person_id,
            NutritionPlan.lineage_id == plan.lineage_id,
            NutritionPlan.id != plan.id,
            NutritionPlan.status == "active",
        )
    ).all()
    for previous in other_active:
        if plan.valid_from > previous.valid_from:
            cutoff = plan.valid_from - timedelta(days=1)
            if previous.valid_until is None or previous.valid_until > cutoff:
                previous.valid_until = cutoff
        previous.status = "superseded"
    plan.status = "active"


def create_nutrition_plan(
    db: Session,
    *,
    person: Person,
    data: NutritionPlanCreate,
) -> NutritionPlan:
    plan = NutritionPlan(
        person_id=person.id,
        lineage_id=uuid.uuid4(),
        version=1,
        title=data.title,
        source_type=data.source_type,
        source_name=data.source_name,
        source_reference=data.source_reference,
        original_text=data.original_text,
        status="draft",
        valid_from=data.valid_from,
        valid_until=data.valid_until,
    )
    db.add(plan)
    db.commit()
    return get_nutrition_plan(db, person_id=person.id, plan_id=plan.id) or plan


def create_nutrition_plan_version(
    db: Session,
    *,
    base_plan: NutritionPlan,
    data: NutritionPlanVersionCreate,
) -> NutritionPlan:
    if base_plan.status == "superseded":
        raise NutritionPlanError("A superseded plan cannot be used as the base for a new version.")

    latest_version = db.scalar(
        select(func.max(NutritionPlan.version)).where(
            NutritionPlan.person_id == base_plan.person_id,
            NutritionPlan.lineage_id == base_plan.lineage_id,
        )
    )
    next_version = (latest_version or 0) + 1
    supplied = data.model_fields_set

    version = NutritionPlan(
        person_id=base_plan.person_id,
        lineage_id=base_plan.lineage_id,
        version=next_version,
        supersedes_plan_id=base_plan.id,
        title=data.title if data.title is not None else base_plan.title,
        source_type=data.source_type if data.source_type is not None else base_plan.source_type,
        source_name=data.source_name if "source_name" in supplied else base_plan.source_name,
        source_reference=(
            data.source_reference if "source_reference" in supplied else base_plan.source_reference
        ),
        original_text=(
            data.original_text if "original_text" in supplied else base_plan.original_text
        ),
        status="draft",
        valid_from=data.valid_from if data.valid_from is not None else base_plan.valid_from,
        valid_until=data.valid_until if "valid_until" in supplied else base_plan.valid_until,
    )
    db.add(version)
    db.flush()

    for rule in base_plan.rules:
        db.add(
            NutritionPlanRule(
                nutrition_plan_id=version.id,
                rule_kind=rule.rule_kind,
                nutrition_constraint_id=rule.nutrition_constraint_id,
                nutrition_target_component_id=rule.nutrition_target_component_id,
                nutrition_goal_id=rule.nutrition_goal_id,
                meal_type=rule.meal_type,
                priority=rule.priority,
                valid_from=rule.valid_from,
                valid_until=rule.valid_until,
                source_statement=rule.source_statement,
                applies_outside_plan=rule.applies_outside_plan,
            )
        )

    for guideline in base_plan.guidelines:
        db.add(
            NutritionPlanGuideline(
                nutrition_plan_id=version.id,
                guideline_type=guideline.guideline_type,
                target_type=guideline.target_type,
                target_key=guideline.target_key,
                description=guideline.description,
                meal_type=guideline.meal_type,
                period=guideline.period,
                minimum_occurrences=guideline.minimum_occurrences,
                maximum_occurrences=guideline.maximum_occurrences,
                severity=guideline.severity,
                is_mandatory=guideline.is_mandatory,
                confirmation_status=guideline.confirmation_status,
                priority=guideline.priority,
                valid_from=guideline.valid_from,
                valid_until=guideline.valid_until,
                source_statement=guideline.source_statement,
            )
        )

    db.flush()
    if data.status == "active":
        _activate_plan_lineage(db, version)
    else:
        version.status = data.status
    db.commit()
    return get_nutrition_plan(db, person_id=version.person_id, plan_id=version.id) or version


def update_nutrition_plan(
    db: Session,
    *,
    plan: NutritionPlan,
    data: NutritionPlanUpdate,
) -> NutritionPlan:
    changes = data.model_dump(exclude_unset=True)
    requested_status = changes.pop("status", None)

    if changes and plan.status != "draft":
        raise NutritionPlanError(
            "Active, inactive or superseded plan content is immutable; "
            "create a new version instead."
        )

    if "valid_from" in changes and changes["valid_from"] is None:
        raise NutritionPlanError("valid_from cannot be null")

    for field, value in changes.items():
        setattr(plan, field, value)

    if plan.valid_until is not None and plan.valid_until < plan.valid_from:
        raise NutritionPlanError("valid_until must be on or after valid_from")

    if requested_status is not None and requested_status != plan.status:
        if requested_status not in _ALLOWED_STATUS_TRANSITIONS[plan.status]:
            raise NutritionPlanError(
                f"Invalid nutrition plan status transition: {plan.status} -> {requested_status}."
            )
        if requested_status == "active":
            _activate_plan_lineage(db, plan)
        else:
            plan.status = requested_status

    db.commit()
    return get_nutrition_plan(db, person_id=plan.person_id, plan_id=plan.id) or plan


def delete_nutrition_plan(db: Session, *, plan: NutritionPlan) -> None:
    if plan.status != "draft":
        raise NutritionPlanError(
            "Only draft nutrition plans can be deleted; deactivate active plans instead."
        )
    db.delete(plan)
    db.commit()


def _ensure_plan_editable(plan: NutritionPlan) -> None:
    if plan.status != "draft":
        raise NutritionPlanError(
            "Plan rules and guidelines can only be edited while the plan is draft."
        )


def add_nutrition_plan_rule(
    db: Session,
    *,
    plan: NutritionPlan,
    data: NutritionPlanRuleCreate,
) -> NutritionPlanRule:
    _ensure_plan_editable(plan)

    constraint_id: uuid.UUID | None = None
    target_component_id: uuid.UUID | None = None
    goal_id: uuid.UUID | None = None

    if data.rule_kind == "constraint":
        constraint = db.get(NutritionConstraint, data.reference_id)
        if constraint is None or constraint.person_id != plan.person_id:
            raise NutritionPlanError("Constraint does not belong to the nutrition plan Person.")
        constraint_id = constraint.id
    elif data.rule_kind == "target_component":
        component = db.get(NutritionTargetComponent, data.reference_id)
        if component is None:
            raise NutritionPlanError("Nutrition target component not found.")
        target = db.get(NutritionTarget, component.nutrition_target_id)
        if target is None or target.person_id != plan.person_id:
            raise NutritionPlanError(
                "Target component does not belong to the nutrition plan Person."
            )
        target_component_id = component.id
    else:
        goal = db.get(NutritionGoal, data.reference_id)
        if goal is None or goal.person_id != plan.person_id:
            raise NutritionPlanError("Nutrition goal does not belong to the nutrition plan Person.")
        goal_id = goal.id

    rule = NutritionPlanRule(
        nutrition_plan_id=plan.id,
        rule_kind=data.rule_kind,
        nutrition_constraint_id=constraint_id,
        nutrition_target_component_id=target_component_id,
        nutrition_goal_id=goal_id,
        meal_type=data.meal_type,
        priority=data.priority,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        source_statement=data.source_statement,
        applies_outside_plan=data.applies_outside_plan,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def delete_nutrition_plan_rule(
    db: Session,
    *,
    plan: NutritionPlan,
    rule_id: uuid.UUID,
) -> None:
    _ensure_plan_editable(plan)
    rule = db.scalar(
        select(NutritionPlanRule).where(
            NutritionPlanRule.id == rule_id,
            NutritionPlanRule.nutrition_plan_id == plan.id,
        )
    )
    if rule is None:
        raise NutritionPlanError("Nutrition plan rule not found.")
    db.delete(rule)
    db.commit()


def add_nutrition_plan_guideline(
    db: Session,
    *,
    plan: NutritionPlan,
    data: NutritionPlanGuidelineCreate,
) -> NutritionPlanGuideline:
    _ensure_plan_editable(plan)
    guideline = NutritionPlanGuideline(
        nutrition_plan_id=plan.id,
        **data.model_dump(),
    )
    db.add(guideline)
    db.commit()
    db.refresh(guideline)
    return guideline


def update_nutrition_plan_guideline(
    db: Session,
    *,
    plan: NutritionPlan,
    guideline_id: uuid.UUID,
    data: NutritionPlanGuidelineUpdate,
) -> NutritionPlanGuideline:
    _ensure_plan_editable(plan)
    guideline = db.scalar(
        select(NutritionPlanGuideline).where(
            NutritionPlanGuideline.id == guideline_id,
            NutritionPlanGuideline.nutrition_plan_id == plan.id,
        )
    )
    if guideline is None:
        raise NutritionPlanError("Nutrition plan guideline not found.")
    for field, value in data.model_dump().items():
        setattr(guideline, field, value)
    db.commit()
    db.refresh(guideline)
    return guideline


def delete_nutrition_plan_guideline(
    db: Session,
    *,
    plan: NutritionPlan,
    guideline_id: uuid.UUID,
) -> None:
    _ensure_plan_editable(plan)
    guideline = db.scalar(
        select(NutritionPlanGuideline).where(
            NutritionPlanGuideline.id == guideline_id,
            NutritionPlanGuideline.nutrition_plan_id == plan.id,
        )
    )
    if guideline is None:
        raise NutritionPlanError("Nutrition plan guideline not found.")
    db.delete(guideline)
    db.commit()


def _date_matches(start: date | None, end: date | None, on_date: date) -> bool:
    return (start is None or start <= on_date) and (end is None or end >= on_date)


def _meal_matches(rule_meal_type: str | None, meal_type: MealType) -> bool:
    return rule_meal_type is None or rule_meal_type == meal_type


def _effective_priority(
    *,
    source: str | None,
    local_priority: int,
    mandatory: bool,
) -> int:
    return (10000 if mandatory else 0) + _source_priority(source) + local_priority


def _plan_source(
    plan: NutritionPlan,
    *,
    rule_source: str | None,
) -> EffectiveNutritionPlanSourceRead:
    return EffectiveNutritionPlanSourceRead(
        plan_id=plan.id,
        plan_title=plan.title,
        plan_source_type=plan.source_type,
        source_name=plan.source_name,
        source_reference=plan.source_reference,
        rule_source=rule_source,
    )


def _standalone_source(
    *,
    source: str | None,
    source_name: str | None = None,
    source_reference: str | None = None,
) -> EffectiveNutritionPlanSourceRead:
    return EffectiveNutritionPlanSourceRead(
        plan_id=None,
        plan_title=None,
        plan_source_type=None,
        source_name=source_name,
        source_reference=source_reference,
        rule_source=source,
    )


def _constraint_rule(
    constraint: NutritionConstraint,
    *,
    rule_id: str,
    meal_type: str | None,
    local_priority: int,
    source: EffectiveNutritionPlanSourceRead,
    source_priority: str | None,
) -> EffectiveNutritionNumericRuleRead:
    return EffectiveNutritionNumericRuleRead(
        id=rule_id,
        rule_kind="constraint",
        target_type=constraint.target_type,
        target_key=constraint.target_key,
        operator=constraint.operator,
        value_min=constraint.value_min,
        value_max=constraint.value_max,
        value_target=None,
        unit=constraint.unit,
        severity=constraint.severity,
        is_mandatory=constraint.is_mandatory,
        priority=_effective_priority(
            source=source_priority,
            local_priority=local_priority,
            mandatory=constraint.is_mandatory,
        ),
        meal_type=meal_type,
        source=source,
    )


def _target_rule(
    component: NutritionTargetComponent,
    target: NutritionTarget,
    *,
    rule_id: str,
    meal_type: str | None,
    local_priority: int,
    source: EffectiveNutritionPlanSourceRead,
    source_priority: str | None,
) -> EffectiveNutritionNumericRuleRead:
    if component.value_min is not None and component.value_max is not None:
        operator = "range"
    elif component.value_min is not None:
        operator = "min"
    elif component.value_max is not None:
        operator = "max"
    else:
        operator = "target"
    return EffectiveNutritionNumericRuleRead(
        id=rule_id,
        rule_kind="target_component",
        target_type=component.target_type,
        target_key=component.target_key,
        operator=operator,
        value_min=component.value_min,
        value_max=component.value_max,
        value_target=component.value_target,
        unit=component.unit,
        severity="advisory",
        is_mandatory=False,
        priority=_effective_priority(
            source=source_priority,
            local_priority=local_priority,
            mandatory=False,
        ),
        meal_type=meal_type,
        source=source,
    )


def _goal_read(
    goal: NutritionGoal,
    *,
    rule_id: str,
    local_priority: int,
    source: EffectiveNutritionPlanSourceRead,
    source_priority: str | None,
) -> EffectiveNutritionGoalRead:
    return EffectiveNutritionGoalRead(
        id=rule_id,
        goal_type=goal.goal_type,
        target_weight_kg=goal.target_weight_kg,
        target_rate_kg_per_week=goal.target_rate_kg_per_week,
        target_date=goal.target_date,
        priority=_effective_priority(
            source=source_priority,
            local_priority=local_priority,
            mandatory=False,
        ),
        source=source,
    )


def _detect_numeric_conflicts(
    rules: list[EffectiveNutritionNumericRuleRead],
) -> list[EffectiveNutritionPlanConflictRead]:
    grouped: dict[
        tuple[str, str, str | None],
        list[EffectiveNutritionNumericRuleRead],
    ] = defaultdict(list)
    for rule in rules:
        if rule.value_min is not None or rule.value_max is not None:
            grouped[(rule.target_type, rule.target_key, rule.unit)].append(rule)

    conflicts: list[EffectiveNutritionPlanConflictRead] = []
    ordered_groups = sorted(
        grouped.items(),
        key=lambda item: (item[0][0], item[0][1], item[0][2] or ""),
    )
    for (target_type, target_key, unit), group in ordered_groups:
        lower_rules = [rule for rule in group if rule.value_min is not None]
        upper_rules = [rule for rule in group if rule.value_max is not None]
        if not lower_rules or not upper_rules:
            continue
        lower_rule = max(lower_rules, key=lambda rule: Decimal(rule.value_min or 0))
        upper_rule = min(upper_rules, key=lambda rule: Decimal(rule.value_max or 0))
        lower = lower_rule.value_min
        upper = upper_rule.value_max
        if lower is None or upper is None or lower <= upper:
            continue
        severity = (
            "mandatory"
            if lower_rule.is_mandatory and upper_rule.is_mandatory
            else "advisory"
        )
        conflicts.append(
            EffectiveNutritionPlanConflictRead(
                target_type=target_type,
                target_key=target_key,
                unit=unit,
                severity=severity,
                rule_ids=[lower_rule.id, upper_rule.id],
                message=(
                    f"Conflicting {target_key} guidance: minimum {lower} {unit or ''} "
                    f"exceeds maximum {upper} {unit or ''}."
                ).strip(),
            )
        )
    return conflicts


def compile_effective_nutrition_plan(
    db: Session,
    *,
    person_id: uuid.UUID,
    on_date: date,
    meal_type: MealType,
) -> EffectiveNutritionPlanRead:
    person = db.get(Person, person_id)
    if person is None:
        raise NutritionPlanError("Person not found.")

    active_plans = list(
        db.scalars(
            _plan_query(person_id).where(
                NutritionPlan.status.in_(("active", "superseded")),
                NutritionPlan.valid_from <= on_date,
                or_(NutritionPlan.valid_until.is_(None), NutritionPlan.valid_until >= on_date),
            )
        ).all()
    )
    active_plans.sort(
        key=lambda plan: (
            -_source_priority(plan.source_type),
            plan.lineage_id.hex,
            -plan.version,
        )
    )

    all_plan_only_rules = db.scalars(
        select(NutritionPlanRule)
        .join(NutritionPlan, NutritionPlan.id == NutritionPlanRule.nutrition_plan_id)
        .where(
            NutritionPlan.person_id == person_id,
            NutritionPlanRule.applies_outside_plan.is_(False),
        )
    ).all()
    plan_only_constraint_ids = {
        rule.nutrition_constraint_id
        for rule in all_plan_only_rules
        if rule.nutrition_constraint_id is not None
    }
    plan_only_target_component_ids = {
        rule.nutrition_target_component_id
        for rule in all_plan_only_rules
        if rule.nutrition_target_component_id is not None
    }
    plan_only_goal_ids = {
        rule.nutrition_goal_id
        for rule in all_plan_only_rules
        if rule.nutrition_goal_id is not None
    }

    numeric_rules: list[EffectiveNutritionNumericRuleRead] = []
    goals: list[EffectiveNutritionGoalRead] = []
    guidelines: list[EffectiveNutritionGuidelineRead] = []
    seen_constraint_ids: set[uuid.UUID] = set()
    seen_target_component_ids: set[uuid.UUID] = set()
    seen_goal_ids: set[uuid.UUID] = set()

    for plan in active_plans:
        for binding in plan.rules:
            if not _meal_matches(binding.meal_type, meal_type):
                continue
            if not _date_matches(binding.valid_from, binding.valid_until, on_date):
                continue

            if binding.rule_kind == "constraint" and binding.nutrition_constraint is not None:
                constraint = binding.nutrition_constraint
                if not _date_matches(constraint.start_date, constraint.end_date, on_date):
                    continue
                seen_constraint_ids.add(constraint.id)
                numeric_rules.append(
                    _constraint_rule(
                        constraint,
                        rule_id=f"plan-rule:{binding.id}",
                        meal_type=binding.meal_type,
                        local_priority=binding.priority,
                        source=_plan_source(plan, rule_source=constraint.source),
                        source_priority=plan.source_type,
                    )
                )
            elif (
                binding.rule_kind == "target_component"
                and binding.nutrition_target_component is not None
            ):
                component = binding.nutrition_target_component
                target = component.nutrition_target
                if not _date_matches(
                    target.valid_from,
                    target.valid_until,
                    on_date,
                ):
                    continue
                seen_target_component_ids.add(component.id)
                numeric_rules.append(
                    _target_rule(
                        component,
                        target,
                        rule_id=f"plan-rule:{binding.id}",
                        meal_type=binding.meal_type,
                        local_priority=binding.priority,
                        source=_plan_source(plan, rule_source=target.source),
                        source_priority=plan.source_type,
                    )
                )
            elif binding.rule_kind == "goal" and binding.nutrition_goal is not None:
                goal = binding.nutrition_goal
                if goal.start_date > on_date or (goal.target_date and goal.target_date < on_date):
                    continue
                seen_goal_ids.add(goal.id)
                goals.append(
                    _goal_read(
                        goal,
                        rule_id=f"plan-rule:{binding.id}",
                        local_priority=binding.priority,
                        source=_plan_source(plan, rule_source=goal.source),
                        source_priority=plan.source_type,
                    )
                )

        for guideline in plan.guidelines:
            if guideline.confirmation_status != "confirmed":
                continue
            if not _meal_matches(guideline.meal_type, meal_type):
                continue
            if not _date_matches(guideline.valid_from, guideline.valid_until, on_date):
                continue
            guidelines.append(
                EffectiveNutritionGuidelineRead(
                    id=guideline.id,
                    guideline_type=guideline.guideline_type,
                    target_type=guideline.target_type,
                    target_key=guideline.target_key,
                    description=guideline.description,
                    meal_type=guideline.meal_type,
                    period=guideline.period,
                    minimum_occurrences=guideline.minimum_occurrences,
                    maximum_occurrences=guideline.maximum_occurrences,
                    severity=guideline.severity,
                    is_mandatory=guideline.is_mandatory,
                    priority=_effective_priority(
                        source=plan.source_type,
                        local_priority=guideline.priority,
                        mandatory=guideline.is_mandatory,
                    ),
                    confirmation_status="confirmed",
                    source=_plan_source(plan, rule_source=plan.source_type),
                )
            )

    standalone_constraints = db.scalars(
        select(NutritionConstraint).where(
            NutritionConstraint.person_id == person_id,
            or_(
                NutritionConstraint.start_date.is_(None),
                NutritionConstraint.start_date <= on_date,
            ),
            or_(NutritionConstraint.end_date.is_(None), NutritionConstraint.end_date >= on_date),
        )
    ).all()
    for constraint in standalone_constraints:
        if constraint.id in seen_constraint_ids or constraint.id in plan_only_constraint_ids:
            continue
        numeric_rules.append(
            _constraint_rule(
                constraint,
                rule_id=f"constraint:{constraint.id}",
                meal_type=None,
                local_priority=100,
                source=_standalone_source(
                    source=constraint.source,
                    source_name=constraint.source_name,
                    source_reference=constraint.source_reference,
                ),
                source_priority=constraint.source,
            )
        )

    current_target = db.scalar(
        select(NutritionTarget)
        .where(
            NutritionTarget.person_id == person_id,
            NutritionTarget.status == "active",
            NutritionTarget.valid_from <= on_date,
            or_(NutritionTarget.valid_until.is_(None), NutritionTarget.valid_until >= on_date),
        )
        .options(selectinload(NutritionTarget.components))
        .order_by(NutritionTarget.valid_from.desc(), NutritionTarget.created_at.desc())
        .limit(1)
    )
    if current_target is not None:
        for component in current_target.components:
            if (
                component.id in seen_target_component_ids
                or component.id in plan_only_target_component_ids
            ):
                continue
            numeric_rules.append(
                _target_rule(
                    component,
                    current_target,
                    rule_id=f"target-component:{component.id}",
                    meal_type=None,
                    local_priority=100,
                    source=_standalone_source(source=current_target.source),
                    source_priority=current_target.source,
                )
            )

    standalone_goals = db.scalars(
        select(NutritionGoal).where(
            NutritionGoal.person_id == person_id,
            NutritionGoal.status == "active",
            NutritionGoal.start_date <= on_date,
            or_(NutritionGoal.target_date.is_(None), NutritionGoal.target_date >= on_date),
        )
    ).all()
    for goal in standalone_goals:
        if goal.id in seen_goal_ids or goal.id in plan_only_goal_ids:
            continue
        goals.append(
            _goal_read(
                goal,
                rule_id=f"goal:{goal.id}",
                local_priority=100,
                source=_standalone_source(source=goal.source),
                source_priority=goal.source,
            )
        )

    numeric_rules.sort(
        key=lambda rule: (-rule.priority, rule.target_type, rule.target_key, rule.id)
    )
    goals.sort(key=lambda goal: (-goal.priority, goal.goal_type, goal.id))
    guidelines.sort(key=lambda guideline: (-guideline.priority, str(guideline.id)))

    return EffectiveNutritionPlanRead(
        person_id=person_id,
        effective_date=on_date,
        meal_type=meal_type,
        active_plans=active_plans,
        numeric_rules=numeric_rules,
        goals=goals,
        guidelines=guidelines,
        conflicts=_detect_numeric_conflicts(numeric_rules),
    )
