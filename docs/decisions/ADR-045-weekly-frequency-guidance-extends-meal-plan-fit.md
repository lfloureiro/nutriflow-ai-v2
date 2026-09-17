# ADR-045 — Weekly frequency guidance extends Meal Plan-Fit

## Status

Accepted.

## Context

The Phase 8a weekly-frequency read model established deterministic Person-specific progress for confirmed weekly NutritionPlan guidance. Recommendation paths already use Meal Plan-Fit as the common nutrition and safety evaluator, so adding a second recommendation-specific frequency evaluator would recreate the semantic split removed in earlier phases.

Weekly minimums also have different semantics from meal-scoped mandatory rules: a requirement such as “fish three times per week” does not mean every individual meal must contain fish. A weekly maximum, however, can make a candidate unsafe when the candidate would exceed an authoritative mandatory cap.

## Decision

Weekly frequency evidence becomes part of the server-authoritative Meal Plan-Fit result for an explicit Person, planning date, meal type, candidate and exact portion.

The production Meal Plan-Fit path:

```text
candidate + exact portion
-> ordinary numeric/safety Plan-Fit
-> Person-specific weekly frequency progress
-> explicit candidate planning classification
-> weekly frequency guideline result
-> final eligibility/status
```

Only persisted structured evidence may classify the candidate for frequency guidance. Supported v1 targets are `food_category`, `food_group`, `planning_category`, `primary_protein`, `food_item` and `recipe`. Food names and descriptions are never interpreted as category evidence.

### Minimum frequency semantics

A candidate that explicitly matches a still-confirmed weekly minimum deficit receives `support`. A candidate that does not match the minimum remains neutral; the minimum is not converted into a mandatory per-meal gate because later meals can still satisfy the week-level requirement.

If existing unclassified meals could already satisfy the minimum, the deficit is not treated as confirmed and therefore does not receive deterministic support pressure.

### Maximum frequency semantics

For mandatory weekly maxima:

- a known matching candidate that would definitely exceed the maximum fails;
- if incomplete classification of existing meals or of the candidate means safe remaining capacity cannot be proven, the result is `unknown` and fails closed;
- a known non-match does not consume the maximum.

Advisory frequency guidance may influence ordering but cannot override mandatory Meal Plan-Fit eligibility.

### Recommendation behavior

Recommendation ranking consumes the weekly guideline results already present in Meal Plan-Fit. It does not query or reinterpret weekly guidance independently.

Among candidates that remain eligible after all mandatory Plan-Fit gates, deterministic weekly-minimum `support` is used as an ordering pressure before the existing candidate rank:

1. number of supported mandatory weekly minimums;
2. number of supported advisory weekly minimums;
3. existing rank from nutrition fit, preference, practical context, diversity and feedback;
4. stable candidate key tie-break.

Weekly support does not alter the numeric `fit_score`. The score remains the satisfaction measure for candidate/meal-scoped numeric rules; week-level frequency evidence is represented separately and explicitly.

## Consequences

- One common evaluator remains authoritative for nutrition and weekly frequency semantics.
- Mandatory weekly maxima can block home, pantry, restaurant and delivery candidates through the same Plan-Fit evidence.
- Mandatory weekly minimums guide adaptive selection without incorrectly forcing every meal to satisfy the weekly target.
- Missing classification stays visible as uncertainty and is never converted to zero or a negative match.
- Recommendation decisions can preserve whether weekly-frequency support affected ordering through the engine version and run context.

## Deferred

This slice is adaptive candidate selection for an individual meal slot, not a combinatorial optimizer for an entire week. Deferred work includes:

- simultaneous multi-slot week optimization;
- participant-specific aggregation for shared-Family recommendations;
- richer reviewed food-category taxonomy/equivalence;
- automatic qualitative-guideline inference;
- batch optimization of candidate Plan-Fit evaluation;
- removal of the existing private candidate-loader dependency used by Meal Plan-Fit.
