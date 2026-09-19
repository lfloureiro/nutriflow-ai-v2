# AI-assisted nutrition-plan import

NutriFlow accepts unstructured recommendation text through the same review boundary as deterministic plan imports.

## Flow

```text
source text
-> deterministic parser OR structured AI interpreter
-> proposed import items
-> explicit human confirm/reject
-> materialize confirmed items into draft NutritionPlan
-> explicit activation
```

The AI path never confirms, applies or activates recommendations automatically. It preserves a source excerpt on every proposal and returns ambiguous content as `unclassified` rather than inventing a rule.

Explicit prohibitions such as "avoid soy" can be preserved as structured exclusion proposals. For persistence compatibility these use the existing `numeric_rule` proposal envelope with `operator=exclude`, a canonical `target_type/target_key`, and null numeric values/unit. Confirmed exclusions materialize as `NutritionConstraint` rows. A structured exclusion does not authorize runtime name matching: if candidate evidence cannot prove the category/subject, Plan-Fit keeps that evidence unknown/not evaluated.

## Configuration

- `OPENAI_API_KEY`: enables AI interpretation.
- `NUTRIFLOW_NUTRITION_PLAN_AI_MODEL`: optional model override; defaults to `gpt-5.6-luna`.
- `OPENAI_BASE_URL`: optional API base override; defaults to `https://api.openai.com/v1`.

When AI is unavailable, the existing deterministic parser remains usable.

## ChatGPT-assisted mode without API credentials

When the user has ChatGPT access but no OpenAI API key, NutriFlow can generate a copyable prompt from the extracted document text and the import JSON schema. The user runs that prompt in ChatGPT and pastes the JSON response back into NutriFlow. The pasted response is parsed and validated server-side before any import session is created.

This mode does not automate the ChatGPT web application, store session cookies, or bypass the human review boundary. Invalid JSON or proposal shapes fail closed.

## Current input boundary

The first browser slice accepts pasted text. PDF, DOCX and image extraction will feed the same source-text/import-session contract in a follow-up, so document formats do not bypass review or provenance.
