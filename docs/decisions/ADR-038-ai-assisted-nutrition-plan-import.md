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
- may classify numeric rules, explicit structured exclusions, qualitative guidance, weekly frequency guidance, or leave text unclassified;
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

For users without an API key, NutriFlow also supports a manual ChatGPT-assisted bridge. NutriFlow generates a strict prompt containing the extracted source text and the same structured-output schema; the user copies that prompt into ChatGPT and pastes the returned JSON back into NutriFlow. The backend parses and validates that JSON against the normal import proposal schema before creating a review session. NutriFlow does not automate `chatgpt.com`, reuse browser cookies, or treat pasted output as trusted.

The OpenAI request uses the Responses API with JSON-schema Structured Outputs and `store=false`.

### Structured exclusions

The existing persisted import envelope remains backward-compatible: an explicit exclusion is represented as `proposal_type=numeric_rule` with `operator=exclude`, a normalized `target_type/target_key`, and no numeric values or unit. The historical proposal-type name is retained to avoid a persistence migration; validation distinguishes numeric rules from exclusion rules by operator.

Explicit multi-subject prohibitions should be split into one review proposal per subject. The interpreter must not invent catalogue identifiers or infer that a Recipe contains a category. Materialization creates a normal `NutritionConstraint`; runtime enforcement remains dependent on explicit candidate evidence. Unsupported category evidence therefore remains partial/unknown rather than being inferred from names.

## Consequences
- AI output remains advisory and reviewable rather than authoritative.
- Existing provenance and immutable-active-plan rules remain unchanged.
- A failed AI request does not create a partial plan or import session.
- Document extraction (PDF/DOCX/image) can feed this same source-text boundary without changing the review/materialization contract.
- Image/document extraction and manual editing of unclassified proposals remain follow-up work.
