# ADR-044 — Weekly frequency progress uses structured meal evidence

## Status

Accepted for Phase 8 foundation.

## Context

Nutrition Plans already represent confirmed weekly frequency guidance with structured fields such as `target_type`, `target_key`, `minimum_occurrences` and `maximum_occurrences`. Until now those guidelines were surfaced by EffectiveNutritionPlan but deliberately not evaluated by Meal Plan-Fit, because one candidate meal cannot determine whole-week compliance.

Phase 8 needs a deterministic weekly context before any adaptive week optimizer can use frequency guidance. The system must count Person-specific meal participation without guessing categories from dish names, descriptions or model inference.

The deterministic text import currently emits weekly food-group statements as `target_type=food_category`, so the progress evaluator must consume that same canonical vocabulary rather than creating a semantic split between ingestion and evaluation.

## Decision

Add a server-authoritative weekly frequency progress read model and endpoint.

The week is Monday through Sunday in the Person's persisted IANA timezone. The requested date is only an anchor for selecting that local week.

Frequency guidelines are obtained from the existing EffectiveNutritionPlan compiler across the four supported meal types and deduplicated by guideline id. Only confirmed `frequency` guidelines with `period=week` participate.

Occurrences are Person-specific. A shared MealEvent contributes only when the selected Person has a non-skipped, non-replaced MealParticipant and a matching non-skipped, non-replaced Serving.

Cancelled and replaced MealEvents are excluded. Skipped and replaced participants/servings are excluded.

One MealEvent contributes at most one occurrence to one frequency guideline, even if multiple servings in that event match the same target.

Completed and planned occurrences are reported separately. Consumed/partial participant or serving evidence, or a completed MealEvent for a participating Person, is treated as completed; other valid occurrences are planned.

### Structured target matching

No food name or description matching is allowed.

Supported target types in v1 are:

- `food_category`: canonical target emitted by Nutrition Plan import; exact normalized match against explicit `MealCandidatePlanningProfile.planning_category` or `primary_protein`;
- `food_group`: backward-compatible alias resolved with the same explicit metadata;
- `planning_category`: exact normalized match against `planning_category`;
- `primary_protein`: exact normalized match against `primary_protein`;
- `food_item`: exact match against the referenced FoodItem `catalog_key`;
- `recipe`: exact match against the referenced Recipe `recipe_key`.

`food_category` and the legacy `food_group` alias are resolved only from persisted structured planning metadata, never from food names or descriptions. A category such as `fish` can therefore match an explicit `primary_protein=fish`; absent that evidence, the system does not guess.

If the target type/key is unsupported, progress is `unknown` rather than silently treated as zero. Numeric occurrence/progress fields are therefore `null` for unsupported targets, not zero.

If an otherwise relevant meal lacks enough structured classification evidence to decide whether it matches, it is counted as unclassified. Reported matching counts then become a lower bound. Missing classification evidence is not equivalent to a confirmed non-match.

### Progress semantics

The read model exposes completed, planned and total confirmed occurrences, remaining minimum, remaining capacity, unclassified meal count, whether counts are a lower bound, source provenance, and the matching MealEvents.

A maximum is `exceeded` only when confirmed occurrences exceed it. A minimum is `achieved` when confirmed occurrences reach it. Unsupported targets remain `unknown`. Other evaluable states are `in_progress`.

This endpoint does not yet mutate recommendations or construct a weekly meal plan. It provides the deterministic context that later Phase 8 planning can consume.

## Consequences

- weekly frequency guidance becomes measurable without changing Meal Plan-Fit's meal-scoped semantics;
- imported weekly `food_category` guidance and runtime progress use the same structured vocabulary;
- Family meals remain Person-specific for frequency counting;
- timezone boundaries are deterministic and local to the Person;
- missing classification stays explicit;
- unsupported evidence remains unknown rather than being represented as a numeric zero;
- adaptive weekly planning can later use the same evidence rather than inventing a second frequency evaluator.

## Deferred

- hard-gating future candidates from mandatory weekly maxima;
- optimization across all meals in a week;
- richer taxonomy/equivalence between food categories;
- AI-assisted classification without persisted reviewed evidence;
- browser-side frequency calculations.
