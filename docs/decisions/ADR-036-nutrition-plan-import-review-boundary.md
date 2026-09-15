# ADR-036 — Nutrition plan import review boundary

## Status

Accepted.

## Context

NutriFlow can now represent versioned NutritionPlans and compile an EffectiveNutritionPlan. The next requirement is to accept free-text plans without allowing parser output to become professional guidance silently.

A parser can be wrong about the nutrient, value, meal scope, mandatory/advisory status or weekly frequency. Creating active NutritionConstraint or NutritionPlanGuideline rows directly from parser output would blur the distinction between the source document and NutriFlow's interpretation.

## Decision

Nutrition-plan import uses an explicit staging and review boundary.

```text
source text
-> NutritionPlanImportSession
-> NutritionPlanImportProposal[]
-> explicit confirm/reject/edit
-> apply confirmed proposals to a draft NutritionPlan
-> separate NutritionPlan activation
```

### Import session

An import session owns one newly created draft NutritionPlan and preserves:

- the exact source text;
- parser name/version;
- review/applied/cancelled lifecycle;
- the generated proposal set.

### Proposals

Each source statement becomes one proposal with:

- the verbatim source statement;
- normalized interpretation fields;
- parser confidence and note;
- proposed/confirmed/rejected review state;
- optional materialized plan-rule/guideline reference.

Statements that cannot be interpreted safely are retained as `unclassified`; they are not discarded or guessed.

### Apply boundary

Apply is allowed only when every proposal has been explicitly confirmed or rejected. A confirmed `unclassified` proposal blocks apply until it is edited into a supported type or rejected.

Applying an import:

- materializes confirmed numeric proposals as Person NutritionConstraint records bound to the draft plan through NutritionPlanRule;
- materializes qualitative/frequency proposals as confirmed NutritionPlanGuideline records;
- preserves source statement and professional/user provenance;
- does not activate the NutritionPlan.

Activation remains the existing explicit NutritionPlan lifecycle operation.

## Parser strategy

The first parser is deterministic and conservative. It recognizes a narrow set of high-confidence PT/EN patterns for:

- numeric nutrient limits/targets/ranges;
- breakfast/lunch/snack/dinner scope;
- weekly food-category frequencies;
- qualitative directives.

Future LLM/document parsers must emit the same proposal contract and must not bypass review.

## Consequences

Positive:

- parser errors remain reversible and visible;
- source provenance is not overwritten by NutriFlow interpretation;
- no parsed statement silently becomes mandatory professional guidance;
- future parsers can be replaced without changing the downstream domain;
- imported rules enter the same EffectiveNutritionPlan compiler as manually created rules.

Trade-offs:

- import requires an explicit review step;
- the first deterministic parser intentionally leaves some statements unclassified;
- document/PDF/image extraction remains a later adapter over the same staging contract.
