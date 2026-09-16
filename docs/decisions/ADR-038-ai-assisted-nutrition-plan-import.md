# ADR-038 — AI-assisted nutrition-plan import

## Status
Accepted

## Context
Nutrition recommendations often arrive as unstructured prose from a nutritionist or clinician. The existing import domain already preserves source text, creates review proposals and requires explicit confirmation before materialization, but only had a deterministic parser and no user-facing review flow.

## Decision
NutriFlow adds an optional AI interpretation boundary on top of the existing import/review model.

The AI interpreter:
- receives source text only after the user explicitly starts an import;
- uses structured output constrained to the existing import-proposal shape;
- may classify numeric rules, qualitative guidance, weekly frequency guidance, or leave text unclassified;
- must preserve a source statement for provenance;
- must not infer quantities, units, diagnoses or recommendations that are not explicit in the source;
- always creates proposals with `confirmation_status=proposed`;
- never activates a plan or materializes guidance by itself.

The user-facing flow is:

```text
source text
-> deterministic or AI interpretation
-> proposal review
-> explicit confirm/reject for every proposal
-> materialize confirmed proposals into a draft NutritionPlan
-> explicit plan activation
```

The default AI model is `gpt-5.6-luna`, configurable with `NUTRIFLOW_NUTRITION_PLAN_AI_MODEL`. The API key is read from `OPENAI_API_KEY`. AI interpretation fails explicitly when it is not configured; the deterministic parser remains available as a non-AI path.

The OpenAI request uses the Responses API with JSON-schema Structured Outputs and `store=false`.

## Consequences
- AI output remains advisory and reviewable rather than authoritative.
- Existing provenance and immutable-active-plan rules remain unchanged.
- A failed AI request does not create a partial plan or import session.
- Document extraction (PDF/DOCX/image) can feed this same source-text boundary without changing the review/materialization contract.
- Image/document extraction and manual editing of unclassified proposals remain follow-up work.
