# ADR-053: NutritionPlan authority is explicit and derived

## Status

Accepted for the NutritionPlan authority foundation. This decision complements the weekly-planning UX work and is intentionally implemented without a database migration.

## Context

NutriFlow can use several kinds of Person context when recommending meals: food preferences, adverse reactions, pantry state, schedules, recipe composition, standalone clinical constraints, NutritionTargets and NutritionPlans.

Those sources do not all justify the same product claim. In particular, neutral nutrient facts or generic optimisation must not be presented as if a nutritionist/clinician plan prescribed them. AI-extracted document content also remains draft evidence until it is reviewed and explicitly activated as a NutritionPlan.

At the same time, standalone mandatory safety constraints must continue to gate candidates even when no NutritionPlan is active.

## Decision

NutritionPlan authority is a server-authoritative, derived state. It is recomputed from current plan validity, applicable plan-backed rules/guidelines, conflicts and candidate evidence; it is not persisted as a second source of truth.

Consumers receive one of four states:

- `active_plan`: at least one active NutritionPlan applies and applicable plan-backed evidence was evaluated for the decision;
- `partial_plan_coverage`: an active plan exists but no applicable plan rule/guideline covers the decision, or plan-backed evidence is unknown/not evaluated;
- `no_active_plan`: no NutritionPlan applies to the Person/date/meal;
- `plan_conflict`: applicable authoritative guidance contains a mandatory conflict.

The response also exposes provenance through the active plan records and the ids of plan-backed rules/guidelines used. Candidate-level Plan-Fit additionally exposes plan-backed unknown/not-evaluated evidence.

## Claim semantics

Only `active_plan` supports direct product language such as `aligned with the plan` when the specific conclusion is backed by the returned rule/guideline evidence.

`partial_plan_coverage` may show the known evidence and constraints, but must state that nutritional coverage is partial.

`no_active_plan` may still use preferences, adverse reactions, pantry, schedule, price, diversity and neutral nutrition composition. Standalone mandatory constraints continue to gate safety. However, those facts must not be described as NutritionPlan-backed optimisation.

`plan_conflict` prevents a positive plan-alignment claim until the mandatory conflict is reviewed.

## Propagation

`EffectiveNutritionPlanRead` exposes authority for the Person/date/meal context before a candidate is evaluated.

`MealPlanFitRead` exposes candidate-specific authority and downgrades otherwise active plan coverage to partial when plan-backed evidence is unknown or not evaluated.

Downstream recommendation, transformation and weekly-planning APIs should consume this metadata rather than re-inferring authority from free text or from the existence of generic nutrition scores.

## Consequences

- no new persisted authority state can become stale relative to NutritionPlan data;
- imported AI extraction remains non-authoritative until the resulting plan is explicitly activated;
- standalone clinical/safety constraints retain their hard-gate semantics without being mislabeled as NutritionPlan authority;
- recipe transformation can later distinguish `preference/practical variant` from `plan-backed adapted version` safely;
- UI can provide a clear `Importar plano` / `Adicionar plano` path when no active plan exists.
