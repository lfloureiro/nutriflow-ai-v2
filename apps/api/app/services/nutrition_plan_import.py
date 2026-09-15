import re
import uuid
from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.nutrition_constraint import NutritionConstraint
from app.models.nutrition_plan import NutritionPlan, NutritionPlanGuideline, NutritionPlanRule
from app.models.nutrition_plan_import import (
    NutritionPlanImportProposal,
    NutritionPlanImportSession,
)
from app.models.person import Person
from app.schemas.nutrition_plan_import import (
    NutritionPlanImportCreate,
    NutritionPlanImportProposalCreate,
    NutritionPlanImportProposalUpdate,
)

PARSER_NAME = "deterministic-text"
PARSER_VERSION = "nutrition-plan-text-v1"


class NutritionPlanImportError(ValueError):
    pass


_MEAL_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "breakfast",
        (
            "breakfast",
            "pequeno-almoço",
            "pequeno almoço",
            "pequeno almoco",
            "pequeno-almoco",
        ),
    ),
    ("lunch", ("lunch", "almoço", "almoco")),
    ("snack", ("snack", "lanche")),
    ("dinner", ("dinner", "jantar")),
)

_NUTRIENTS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("protein", "g", ("protein", "proteína", "proteina")),
    ("fiber", "g", ("fibre", "fiber", "fibra")),
    ("sodium", "mg", ("sodium", "sódio", "sodio")),
    ("energy", "kcal", ("energy", "energia", "calories", "calorias", "kcal")),
    (
        "saturated_fat",
        "g",
        ("saturated fat", "gordura saturada", "gorduras saturadas"),
    ),
)

_FOOD_CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("fish", ("fish", "peixe")),
    ("pulses", ("pulses", "leguminosas", "legumes secos")),
    ("red_meat", ("red meat", "carne vermelha")),
    ("vegetables", ("vegetables", "vegetais", "hortícolas", "horticolas")),
    ("salad", ("salad", "salada")),
    ("fruit", ("fruit", "fruta")),
    ("nuts", ("nuts", "frutos secos")),
)

_MANDATORY_CUES = (
    "must",
    "mandatory",
    "required",
    "deve",
    "obrigatório",
    "obrigatorio",
    "não exceder",
    "nao exceder",
    "exclude",
    "excluir",
)

_QUALITATIVE_CUES = (
    "prefer",
    "preferir",
    "favour",
    "favor",
    "choose",
    "escolher",
    "reduce",
    "reduzir",
    "avoid",
    "evitar",
    "prioritize",
    "priorizar",
)

_RANGE_RE = re.compile(
    r"(?P<minimum>\d+(?:[.,]\d+)?)\s*(?:-|–|—|a|to)\s*"
    r"(?P<maximum>\d+(?:[.,]\d+)?)\s*(?P<unit>mg|g|kcal)\b",
    re.IGNORECASE,
)
_SYMBOL_RE = re.compile(
    r"(?P<operator>>=|<=|≥|≤|>|<)\s*(?P<value>\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>mg|g|kcal)\b",
    re.IGNORECASE,
)
_TEXT_MIN_RE = re.compile(
    r"(?:at least|minimum|minimo|mínimo|pelo menos)\s*(?:de\s*)?"
    r"(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>mg|g|kcal)\b",
    re.IGNORECASE,
)
_TEXT_MAX_RE = re.compile(
    r"(?:at most|maximum|maximo|máximo|não exceder|nao exceder|até|ate)\s*(?:de\s*)?"
    r"(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>mg|g|kcal)\b",
    re.IGNORECASE,
)
_EXACT_RE = re.compile(
    r"(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>mg|g|kcal)\b",
    re.IGNORECASE,
)
_WEEKLY_COUNT_RE = re.compile(
    r"(?P<operator>>=|<=|≥|≤|>|<)?\s*(?P<count>\d+)\s*"
    r"(?:meals?|refeições?|refeicoes?|vezes?)?\s*(?:/|por\s+|per\s+)?"
    r"(?:week|semana)\b",
    re.IGNORECASE,
)
_WEEKLY_TEXT_MIN_RE = re.compile(
    r"(?:at least|minimum|minimo|mínimo|pelo menos)\s*(?P<count>\d+)\s*"
    r"(?:meals?|refeições?|refeicoes?|vezes?)?\s*(?:por\s+|per\s+)?"
    r"(?:week|semana)\b",
    re.IGNORECASE,
)
_WEEKLY_TEXT_MAX_RE = re.compile(
    r"(?:at most|maximum|maximo|máximo|até|ate)\s*(?P<count>\d+)\s*"
    r"(?:meals?|refeições?|refeicoes?|vezes?)?\s*(?:por\s+|per\s+)?"
    r"(?:week|semana)\b",
    re.IGNORECASE,
)


def _import_query(person_id: uuid.UUID):
    return (
        select(NutritionPlanImportSession)
        .where(NutritionPlanImportSession.person_id == person_id)
        .options(
            selectinload(NutritionPlanImportSession.nutrition_plan),
            selectinload(NutritionPlanImportSession.proposals),
        )
    )


def get_nutrition_plan_import(
    db: Session,
    *,
    person_id: uuid.UUID,
    import_id: uuid.UUID,
) -> NutritionPlanImportSession | None:
    return db.scalar(
        _import_query(person_id).where(NutritionPlanImportSession.id == import_id)
    )


def list_nutrition_plan_imports(
    db: Session,
    *,
    person_id: uuid.UUID,
) -> list[NutritionPlanImportSession]:
    return list(
        db.scalars(
            _import_query(person_id).order_by(NutritionPlanImportSession.created_at.desc())
        ).all()
    )


def _clean_statement(raw: str) -> str:
    statement = raw.strip()
    statement = re.sub(r"^[\s\-•*]+", "", statement)
    statement = re.sub(r"^\d+[.)]\s*", "", statement)
    return statement.strip()


def _statement_lines(source_text: str) -> list[str]:
    statements = [_clean_statement(item) for item in re.split(r"[\n;]+", source_text)]
    return [statement for statement in statements if statement]


def _decimal(value: str) -> Decimal:
    return Decimal(value.replace(",", "."))


def _find_meal_type(text: str) -> str | None:
    lowered = text.lower()
    for meal_type, markers in _MEAL_MARKERS:
        if any(marker in lowered for marker in markers):
            return meal_type
    return None


def _find_nutrient(text: str) -> tuple[str, str] | None:
    lowered = text.lower()
    for target_key, default_unit, markers in _NUTRIENTS:
        if any(marker in lowered for marker in markers):
            return target_key, default_unit
    return None


def _find_food_category(text: str) -> str | None:
    lowered = text.lower()
    for target_key, markers in _FOOD_CATEGORIES:
        if any(marker in lowered for marker in markers):
            return target_key
    return None


def _is_mandatory(text: str) -> bool:
    lowered = text.lower()
    return any(cue in lowered for cue in _MANDATORY_CUES)


def _numeric_fields(statement: str) -> dict[str, object] | None:
    nutrient = _find_nutrient(statement)
    if nutrient is None:
        return None
    target_key, default_unit = nutrient

    range_match = _RANGE_RE.search(statement)
    if range_match is not None:
        return {
            "target_type": "nutrient",
            "target_key": target_key,
            "operator": "range",
            "value_min": _decimal(range_match.group("minimum")),
            "value_max": _decimal(range_match.group("maximum")),
            "unit": range_match.group("unit").lower(),
            "confidence": Decimal("0.9500"),
        }

    symbol_match = _SYMBOL_RE.search(statement)
    if symbol_match is not None:
        operator = symbol_match.group("operator")
        value = _decimal(symbol_match.group("value"))
        fields: dict[str, object] = {
            "target_type": "nutrient",
            "target_key": target_key,
            "unit": symbol_match.group("unit").lower(),
            "confidence": Decimal("0.9500"),
        }
        if operator in {">=", ">", "≥"}:
            fields.update(operator="min", value_min=value)
        else:
            fields.update(operator="max", value_max=value)
        return fields

    minimum_match = _TEXT_MIN_RE.search(statement)
    if minimum_match is not None:
        return {
            "target_type": "nutrient",
            "target_key": target_key,
            "operator": "min",
            "value_min": _decimal(minimum_match.group("value")),
            "unit": minimum_match.group("unit").lower(),
            "confidence": Decimal("0.9000"),
        }

    maximum_match = _TEXT_MAX_RE.search(statement)
    if maximum_match is not None:
        return {
            "target_type": "nutrient",
            "target_key": target_key,
            "operator": "max",
            "value_max": _decimal(maximum_match.group("value")),
            "unit": maximum_match.group("unit").lower(),
            "confidence": Decimal("0.9000"),
        }

    exact_match = _EXACT_RE.search(statement)
    if exact_match is None:
        return None
    return {
        "target_type": "nutrient",
        "target_key": target_key,
        "operator": "target",
        "value_target": _decimal(exact_match.group("value")),
        "unit": exact_match.group("unit").lower() or default_unit,
        "confidence": Decimal("0.7500"),
    }


def _weekly_fields(statement: str) -> dict[str, object] | None:
    category = _find_food_category(statement)
    if category is None:
        return None

    minimum_match = _WEEKLY_TEXT_MIN_RE.search(statement)
    if minimum_match is not None:
        return {
            "target_type": "food_category",
            "target_key": category,
            "minimum_occurrences": int(minimum_match.group("count")),
            "confidence": Decimal("0.9000"),
        }

    maximum_match = _WEEKLY_TEXT_MAX_RE.search(statement)
    if maximum_match is not None:
        return {
            "target_type": "food_category",
            "target_key": category,
            "maximum_occurrences": int(maximum_match.group("count")),
            "confidence": Decimal("0.9000"),
        }

    count_match = _WEEKLY_COUNT_RE.search(statement)
    if count_match is None:
        return None
    operator = count_match.group("operator")
    count = int(count_match.group("count"))
    fields: dict[str, object] = {
        "target_type": "food_category",
        "target_key": category,
        "confidence": Decimal("0.8500"),
    }
    if operator in {"<=", "<", "≤"}:
        fields["maximum_occurrences"] = count
    else:
        fields["minimum_occurrences"] = count
    return fields


def _parse_statement(statement: str, ordinal: int) -> NutritionPlanImportProposal:
    mandatory = _is_mandatory(statement)
    common = {
        "ordinal": ordinal,
        "source_statement": statement,
        "meal_type": _find_meal_type(statement),
        "severity": "required" if mandatory else "advisory",
        "is_mandatory": mandatory,
        "priority": 100,
        "confirmation_status": "proposed",
    }

    numeric = _numeric_fields(statement)
    if numeric is not None:
        return NutritionPlanImportProposal(
            proposal_type="numeric_rule",
            parser_note="Known nutrient and numeric expression parsed deterministically.",
            **common,
            **numeric,
        )

    weekly = _weekly_fields(statement)
    if weekly is not None:
        return NutritionPlanImportProposal(
            proposal_type="frequency_guideline",
            description=statement,
            period="week",
            parser_note="Weekly food-category frequency parsed deterministically.",
            **common,
            **weekly,
        )

    lowered = statement.lower()
    if any(cue in lowered for cue in _QUALITATIVE_CUES):
        nutrient = _find_nutrient(statement)
        category = _find_food_category(statement)
        target_type: str | None = None
        target_key: str | None = None
        if nutrient is not None:
            target_type = "nutrient"
            target_key = nutrient[0]
        elif category is not None:
            target_type = "food_category"
            target_key = category
        return NutritionPlanImportProposal(
            proposal_type="qualitative_guideline",
            target_type=target_type,
            target_key=target_key,
            description=statement,
            confidence=Decimal("0.8000"),
            parser_note="Qualitative directive detected; wording is preserved verbatim.",
            **common,
        )

    return NutritionPlanImportProposal(
        proposal_type="unclassified",
        description=statement,
        confidence=Decimal("0.2500"),
        parser_note="No safe deterministic interpretation was found; manual review is required.",
        **common,
    )


def create_nutrition_plan_import(
    db: Session,
    *,
    person: Person,
    data: NutritionPlanImportCreate,
) -> NutritionPlanImportSession:
    plan = NutritionPlan(
        person_id=person.id,
        lineage_id=uuid.uuid4(),
        version=1,
        title=data.title,
        source_type=data.source_type,
        source_name=data.source_name,
        source_reference=data.source_reference,
        original_text=data.source_text,
        status="draft",
        valid_from=data.valid_from,
        valid_until=data.valid_until,
    )
    db.add(plan)
    db.flush()

    statements = _statement_lines(data.source_text)
    session = NutritionPlanImportSession(
        person_id=person.id,
        nutrition_plan_id=plan.id,
        parser_name=PARSER_NAME,
        parser_version=PARSER_VERSION,
        status="review",
        source_text=data.source_text,
        parse_summary=f"Parsed {len(statements)} source statement(s) for explicit review.",
    )
    db.add(session)
    db.flush()

    for ordinal, statement in enumerate(statements, start=1):
        proposal = _parse_statement(statement, ordinal)
        proposal.import_session_id = session.id
        db.add(proposal)

    db.commit()
    return get_nutrition_plan_import(db, person_id=person.id, import_id=session.id) or session


def _ensure_review_session(import_session: NutritionPlanImportSession) -> None:
    if import_session.status != "review":
        raise NutritionPlanImportError("Only imports in review can be edited or applied.")
    if import_session.nutrition_plan.status != "draft":
        raise NutritionPlanImportError("The imported nutrition plan must remain draft during review.")


def add_nutrition_plan_import_proposal(
    db: Session,
    *,
    import_session: NutritionPlanImportSession,
    data: NutritionPlanImportProposalCreate,
) -> NutritionPlanImportProposal:
    _ensure_review_session(import_session)
    max_ordinal = db.scalar(
        select(func.max(NutritionPlanImportProposal.ordinal)).where(
            NutritionPlanImportProposal.import_session_id == import_session.id
        )
    )
    proposal = NutritionPlanImportProposal(
        import_session_id=import_session.id,
        ordinal=(max_ordinal or 0) + 1,
        **data.model_dump(),
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


def _get_proposal(
    db: Session,
    *,
    import_session: NutritionPlanImportSession,
    proposal_id: uuid.UUID,
) -> NutritionPlanImportProposal:
    proposal = db.scalar(
        select(NutritionPlanImportProposal).where(
            NutritionPlanImportProposal.id == proposal_id,
            NutritionPlanImportProposal.import_session_id == import_session.id,
        )
    )
    if proposal is None:
        raise NutritionPlanImportError("Nutrition plan import proposal not found.")
    return proposal


def _proposal_payload(proposal: NutritionPlanImportProposal) -> dict[str, object]:
    return {
        "source_statement": proposal.source_statement,
        "proposal_type": proposal.proposal_type,
        "target_type": proposal.target_type,
        "target_key": proposal.target_key,
        "operator": proposal.operator,
        "value_min": proposal.value_min,
        "value_max": proposal.value_max,
        "value_target": proposal.value_target,
        "unit": proposal.unit,
        "description": proposal.description,
        "meal_type": proposal.meal_type,
        "period": proposal.period,
        "minimum_occurrences": proposal.minimum_occurrences,
        "maximum_occurrences": proposal.maximum_occurrences,
        "severity": proposal.severity,
        "is_mandatory": proposal.is_mandatory,
        "priority": proposal.priority,
        "valid_from": proposal.valid_from,
        "valid_until": proposal.valid_until,
        "confidence": proposal.confidence,
        "confirmation_status": proposal.confirmation_status,
        "parser_note": proposal.parser_note,
        "review_notes": proposal.review_notes,
    }


def _validate_proposal_payload(payload: dict[str, object]) -> None:
    try:
        NutritionPlanImportProposalCreate(**payload)
    except ValidationError as exc:
        first_error = exc.errors()[0]
        message = str(first_error.get("msg", "Invalid proposal shape"))
        raise NutritionPlanImportError(f"Invalid nutrition plan import proposal: {message}.") from exc


def update_nutrition_plan_import_proposal(
    db: Session,
    *,
    import_session: NutritionPlanImportSession,
    proposal_id: uuid.UUID,
    data: NutritionPlanImportProposalUpdate,
) -> NutritionPlanImportProposal:
    _ensure_review_session(import_session)
    proposal = _get_proposal(
        db,
        import_session=import_session,
        proposal_id=proposal_id,
    )
    if proposal.nutrition_plan_rule_id is not None or proposal.nutrition_plan_guideline_id is not None:
        raise NutritionPlanImportError("Materialized proposals are immutable.")

    changes = data.model_dump(exclude_unset=True)
    candidate = _proposal_payload(proposal)
    candidate.update(changes)
    _validate_proposal_payload(candidate)

    for field, value in changes.items():
        setattr(proposal, field, value)

    db.commit()
    db.refresh(proposal)
    return proposal


def _validate_confirmed_proposal(proposal: NutritionPlanImportProposal) -> None:
    if proposal.proposal_type == "unclassified":
        raise NutritionPlanImportError(
            f"Confirmed proposal {proposal.id} is still unclassified; edit or reject it first."
        )
    _validate_proposal_payload(_proposal_payload(proposal))


def _materialize_numeric_rule(
    db: Session,
    *,
    plan: NutritionPlan,
    proposal: NutritionPlanImportProposal,
) -> None:
    value_min = proposal.value_min
    value_max = proposal.value_max
    if proposal.value_target is not None:
        value_min = proposal.value_target
        value_max = proposal.value_target

    constraint = NutritionConstraint(
        person_id=plan.person_id,
        constraint_type="nutrient_limit" if proposal.is_mandatory else "nutrient_target",
        target_type=proposal.target_type or "nutrient",
        target_key=proposal.target_key or "unknown",
        operator=proposal.operator or "range",
        value_min=value_min,
        value_max=value_max,
        unit=proposal.unit,
        severity=proposal.severity,
        is_mandatory=proposal.is_mandatory,
        source=plan.source_type,
        source_name=plan.source_name,
        source_reference=plan.source_reference,
        start_date=proposal.valid_from or plan.valid_from,
        end_date=proposal.valid_until or plan.valid_until,
        notes=f"Materialized from nutrition plan import proposal {proposal.id}.",
    )
    db.add(constraint)
    db.flush()

    rule = NutritionPlanRule(
        nutrition_plan_id=plan.id,
        rule_kind="constraint",
        nutrition_constraint_id=constraint.id,
        meal_type=proposal.meal_type,
        priority=proposal.priority,
        valid_from=proposal.valid_from,
        valid_until=proposal.valid_until,
        source_statement=proposal.source_statement,
        applies_outside_plan=False,
    )
    db.add(rule)
    db.flush()
    proposal.nutrition_plan_rule_id = rule.id


def _materialize_guideline(
    db: Session,
    *,
    plan: NutritionPlan,
    proposal: NutritionPlanImportProposal,
) -> None:
    guideline = NutritionPlanGuideline(
        nutrition_plan_id=plan.id,
        guideline_type=(
            "frequency" if proposal.proposal_type == "frequency_guideline" else "qualitative"
        ),
        target_type=proposal.target_type,
        target_key=proposal.target_key,
        description=proposal.description or proposal.source_statement,
        meal_type=proposal.meal_type,
        period=proposal.period,
        minimum_occurrences=proposal.minimum_occurrences,
        maximum_occurrences=proposal.maximum_occurrences,
        severity=proposal.severity,
        is_mandatory=proposal.is_mandatory,
        confirmation_status="confirmed",
        priority=proposal.priority,
        valid_from=proposal.valid_from,
        valid_until=proposal.valid_until,
        source_statement=proposal.source_statement,
    )
    db.add(guideline)
    db.flush()
    proposal.nutrition_plan_guideline_id = guideline.id


def apply_nutrition_plan_import(
    db: Session,
    *,
    import_session: NutritionPlanImportSession,
) -> NutritionPlanImportSession:
    _ensure_review_session(import_session)
    proposals = list(import_session.proposals)
    if any(proposal.confirmation_status == "proposed" for proposal in proposals):
        raise NutritionPlanImportError(
            "Every import proposal must be explicitly confirmed or rejected before apply."
        )

    confirmed = [
        proposal for proposal in proposals if proposal.confirmation_status == "confirmed"
    ]
    if not confirmed:
        raise NutritionPlanImportError("At least one proposal must be confirmed before apply.")

    for proposal in confirmed:
        _validate_confirmed_proposal(proposal)

    plan = import_session.nutrition_plan
    for proposal in confirmed:
        if proposal.proposal_type == "numeric_rule":
            _materialize_numeric_rule(db, plan=plan, proposal=proposal)
        else:
            _materialize_guideline(db, plan=plan, proposal=proposal)

    import_session.status = "applied"
    db.commit()
    return (
        get_nutrition_plan_import(
            db,
            person_id=import_session.person_id,
            import_id=import_session.id,
        )
        or import_session
    )


def cancel_nutrition_plan_import(
    db: Session,
    *,
    import_session: NutritionPlanImportSession,
) -> NutritionPlanImportSession:
    _ensure_review_session(import_session)
    import_session.status = "cancelled"
    db.commit()
    return (
        get_nutrition_plan_import(
            db,
            person_id=import_session.person_id,
            import_id=import_session.id,
        )
        or import_session
    )
