# ADR-037: Meal Plan-Fit evaluation boundary

Status: Accepted

Date: 2026-09-15

## Context

NutriFlow already has two relevant capabilities:

1. `EffectiveNutritionPlan`, which compiles the applicable Person/date/meal guidance with provenance and conflict information.
2. The meal recommendation engine, which already normalizes FoodItem/Recipe composition evidence and applies daily-state, preference and practical-context ranking.

The platform now needs a source-independent answer to a different question: **how well does this specific meal candidate fit the effective nutrition guidance for this Person and meal context?**

This result must later be reusable by home recipe recommendations, meal transformations and restaurant/delivery candidates. It must not be hidden inside one recommendation entrypoint or provider adapter.

## Decision

Introduce a server-authoritative, deterministic `MealPlanFit` calculation.

`MealPlanFit` is calculated on demand and is not persisted in v1. Its inputs are Person, date, meal type, one normalized catalogue candidate (FoodItem or Recipe composition snapshot and portion), plus optional DailyNutritionState context.

The evaluator reuses the existing candidate normalization and safe unit-conversion code. It consumes `EffectiveNutritionPlan` rather than rebuilding plan precedence itself.

### Rule scope

Rules explicitly scoped to the selected meal are compared directly with candidate composition evidence.

Global nutrient rules are treated as daily-context rules. When a DailyNutritionState exists, the evaluator compares the projected daily total after adding the candidate. A daily minimum that is not yet reached can return `support`; one meal is not required to complete the full daily minimum.

Mandatory daily rules without enough daily context or candidate evidence fail closed as `unknown`; they never become an implicit pass.

### Safety and eligibility

Mandatory adverse reactions, mandatory rule failures, mandatory unresolved evidence and mandatory effective-plan conflicts remain independent hard gates. A high numeric fit score cannot override them.

### Score

`fit_score` is secondary evidence, not an eligibility decision. In v1 it is the mean 0..1 satisfaction of scored candidate-level and meal-scoped numeric rules. Daily-progress rules, qualitative guidance and weekly-frequency guidance are not folded into this score.

This intentionally permits a candidate to have a high fit score while still being blocked by a mandatory safety or daily-limit rule. The API exposes both values so the UI does not conflate them.

### Qualitative and frequency guidance

Confirmed qualitative and weekly-frequency guidance remains visible with provenance, but is returned as `not_evaluated` until the platform has reliable evidence/progress semantics for those rule types. Mandatory un-evaluable guidance keeps the result fail-closed.

## API boundary

The initial endpoint is:

`POST /api/persons/{person_id}/meal-plan-fit`

It accepts the same normalized candidate identity used by recommendations (`candidate_kind`, composition snapshot, quantity and unit), avoiding source-specific scoring contracts.

The response includes candidate nutrition evidence, overall status and eligibility, fit score, active plans, conflicts, safety issues, rule-level results, guideline results and explanations.

## Consequences

- Plan-Fit can be reused for recipes, FoodItems and future normalized restaurant/delivery dishes.
- Existing recommendation preference/practical scoring remains separate for now.
- A later recommendation refactor can consume Plan-Fit instead of duplicating nutrition-rule evaluation.
- Meal Transformation can compare before/after Plan-Fit using the same evaluator.
- Weekly-frequency progress and qualitative evidence need dedicated later capabilities rather than guessed scoring.
- No database migration is required for this phase.
