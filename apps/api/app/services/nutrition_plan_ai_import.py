import json
import uuid
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.nutrition_plan import NutritionPlan
from app.models.nutrition_plan_import import (
    NutritionPlanImportProposal,
    NutritionPlanImportSession,
)
from app.models.person import Person
from app.schemas.nutrition_plan_import import (
    NutritionPlanImportCreate,
    NutritionPlanImportProposalCreate,
)
from app.services.nutrition_plan_import import get_nutrition_plan_import

AI_PARSER_NAME = "openai-responses"
AI_PARSER_VERSION = "nutrition-plan-structured-v1"
CHATGPT_ASSISTED_PARSER_NAME = "chatgpt-assisted"
CHATGPT_ASSISTED_PARSER_VERSION = "nutrition-plan-structured-v1:manual-chatgpt"
DEFAULT_MODEL = "gpt-5.6-luna"


class NutritionPlanAIImportError(ValueError):
    pass


def _nullable(kind: str) -> dict[str, object]:
    return {"type": [kind, "null"]}


def _proposal_schema() -> dict[str, object]:
    properties: dict[str, object] = {
        "source_statement": {"type": "string", "minLength": 1},
        "proposal_type": {
            "type": "string",
            "enum": [
                "numeric_rule",
                "qualitative_guideline",
                "frequency_guideline",
                "unclassified",
            ],
        },
        "target_type": _nullable("string"),
        "target_key": _nullable("string"),
        "operator": _nullable("string"),
        "value_min": _nullable("number"),
        "value_max": _nullable("number"),
        "value_target": _nullable("number"),
        "unit": _nullable("string"),
        "description": _nullable("string"),
        "meal_type": {
            "type": ["string", "null"],
            "enum": ["breakfast", "lunch", "snack", "dinner", None],
        },
        "period": {"type": ["string", "null"], "enum": ["week", None]},
        "minimum_occurrences": _nullable("integer"),
        "maximum_occurrences": _nullable("integer"),
        "severity": {"type": "string"},
        "is_mandatory": {"type": "boolean"},
        "priority": {"type": "integer", "minimum": 0, "maximum": 10000},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "parser_note": _nullable("string"),
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties),
    }


def _response_schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "proposals": {
                "type": "array",
                "items": _proposal_schema(),
            },
            "summary": {"type": "string"},
        },
        "required": ["proposals", "summary"],
    }


_INSTRUCTIONS = """You extract nutrition-plan recommendations from source text written by a nutritionist,
clinician, or user. Return only recommendations explicitly supported by the source.

Rules:
- Preserve source_statement as a short verbatim excerpt from the supplied text.
- Never invent quantities, units, meals, frequencies, restrictions, diagnoses, or clinical meaning.
- If wording is ambiguous, use proposal_type='unclassified' and explain the uncertainty in parser_note.
- Use numeric_rule only when an explicit numeric target or limit exists.
- Use qualitative_guideline for explicit non-numeric advice.
- Use frequency_guideline only for explicit weekly frequencies.
- meal_type must be breakfast, lunch, snack, dinner, or null.
- Normalize common nutrient keys to English snake_case, e.g. protein, fiber, sodium, energy_kcal,
  saturated_fat. Food categories may also use concise snake_case keys.
- operator should be min, max, range, or target for numeric rules.
- mandatory=true only when the source clearly states a requirement, prohibition, limit, or obligation;
  otherwise false.
- Keep every proposal confirmation-neutral. The application will require human confirmation later.
- Do not provide medical advice or infer recommendations from diagnoses or laboratory values.
"""


def build_chatgpt_nutrition_plan_prompt(source_text: str) -> str:
    schema = json.dumps(_response_schema(), ensure_ascii=False, indent=2)
    return (
        "You are helping NutriFlow interpret a nutritionist plan.\n\n"
        f"{_INSTRUCTIONS}\n"
        "Return ONLY one JSON object. Do not use Markdown fences and do not add commentary.\n"
        "The JSON must match this schema exactly:\n\n"
        f"{schema}\n\n"
        "SOURCE TEXT START\n"
        f"{source_text.strip()}\n"
        "SOURCE TEXT END\n"
    )


def _parse_chatgpt_response(response_text: str) -> tuple[list[dict[str, object]], str]:
    text = response_text.strip()
    fence = "`" * 3
    if text.startswith(fence):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == fence:
            lines = lines[1:-1]
            if lines and lines[0].strip().casefold() == "json":
                lines = lines[1:]
            text = "\n".join(lines).strip()
    try:
        structured = json.loads(text)
    except json.JSONDecodeError as exc:
        raise NutritionPlanAIImportError(
            "The ChatGPT response is not valid JSON. Paste only the JSON response."
        ) from exc
    if not isinstance(structured, dict):
        raise NutritionPlanAIImportError("The ChatGPT response must be one JSON object.")
    proposals = structured.get("proposals")
    summary = structured.get("summary")
    if not isinstance(proposals, list) or not isinstance(summary, str):
        raise NutritionPlanAIImportError(
            "The ChatGPT response must contain proposals and summary."
        )
    return proposals, summary


def _output_text(payload: dict[str, object]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict) and part.get("type") == "output_text":
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        return text
    raise NutritionPlanAIImportError("The AI interpreter returned no structured output.")


def _call_openai(source_text: str) -> tuple[list[dict[str, object]], str, str]:
    api_key = (settings.openai_api_key or "").strip()
    if not api_key:
        raise NutritionPlanAIImportError(
            "AI interpretation is not configured. Add OPENAI_API_KEY to the NutriFlow .env "
            "file and restart the API."
        )
    model = settings.nutriflow_nutrition_plan_ai_model.strip() or DEFAULT_MODEL
    base_url = settings.openai_base_url.rstrip("/")
    request_payload = {
        "model": model,
        "store": False,
        "instructions": _INSTRUCTIONS,
        "input": source_text,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "nutrition_plan_import",
                "strict": True,
                "schema": _response_schema(),
            }
        },
    }
    request = Request(
        f"{base_url}/responses",
        data=json.dumps(request_payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise NutritionPlanAIImportError(
            f"AI interpretation request failed with HTTP {exc.code}: {detail[:500]}"
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise NutritionPlanAIImportError(f"AI interpretation request failed: {exc}") from exc

    try:
        response_payload = json.loads(raw)
        structured = json.loads(_output_text(response_payload))
    except (json.JSONDecodeError, TypeError) as exc:
        raise NutritionPlanAIImportError("The AI interpreter returned invalid JSON.") from exc
    proposals = structured.get("proposals")
    summary = structured.get("summary")
    if not isinstance(proposals, list) or not isinstance(summary, str):
        raise NutritionPlanAIImportError("The AI interpreter returned an invalid proposal payload.")
    return proposals, summary, model


def _validated_proposals(
    raw_proposals: list[dict[str, object]],
) -> list[NutritionPlanImportProposalCreate]:
    validated: list[NutritionPlanImportProposalCreate] = []
    for raw in raw_proposals:
        candidate = dict(raw)
        candidate["confirmation_status"] = "proposed"
        candidate["valid_from"] = None
        candidate["valid_until"] = None
        candidate["review_notes"] = None
        try:
            validated.append(NutritionPlanImportProposalCreate(**candidate))
        except ValidationError as exc:
            raise NutritionPlanAIImportError(
                "AI interpretation produced a proposal that failed NutriFlow validation."
            ) from exc
    if not validated:
        raise NutritionPlanAIImportError("No recommendations could be extracted from the supplied text.")
    return validated


def create_ai_nutrition_plan_import(
    db: Session,
    *,
    person: Person,
    data: NutritionPlanImportCreate,
) -> NutritionPlanImportSession:
    raw_proposals, summary, model = _call_openai(data.source_text)
    proposals = _validated_proposals(raw_proposals)

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

    import_session = NutritionPlanImportSession(
        person_id=person.id,
        nutrition_plan_id=plan.id,
        parser_name=AI_PARSER_NAME,
        parser_version=f"{AI_PARSER_VERSION}:{model}",
        status="review",
        source_text=data.source_text,
        parse_summary=summary,
    )
    db.add(import_session)
    db.flush()

    for ordinal, proposal_data in enumerate(proposals, start=1):
        values = proposal_data.model_dump()
        values["confidence"] = Decimal(str(values["confidence"]))
        db.add(
            NutritionPlanImportProposal(
                import_session_id=import_session.id,
                ordinal=ordinal,
                **values,
            )
        )

    db.commit()
    return (
        get_nutrition_plan_import(db, person_id=person.id, import_id=import_session.id)
        or import_session
    )
