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

## Configuration

- `OPENAI_API_KEY`: enables AI interpretation.
- `NUTRIFLOW_NUTRITION_PLAN_AI_MODEL`: optional model override; defaults to `gpt-5.6-luna`.
- `OPENAI_BASE_URL`: optional API base override; defaults to `https://api.openai.com/v1`.

When AI is unavailable, the existing deterministic parser remains usable.

## Current input boundary

The first browser slice accepts pasted text. PDF, DOCX and image extraction will feed the same source-text/import-session contract in a follow-up, so document formats do not bypass review or provenance.
