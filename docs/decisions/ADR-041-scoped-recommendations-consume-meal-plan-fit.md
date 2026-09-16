# ADR-041 — Scoped recommendations consume Meal Plan-Fit

## Status

Accepted.

## Context

NutriFlow historically had two nutrition-evaluation paths:

1. the legacy recommendation engine, which directly interpreted `DailyNutritionState`, `NutritionConstraint` and candidate nutrition; and
2. Meal Plan-Fit, which evaluates candidates against `EffectiveNutritionPlan`, professional-plan provenance, mandatory conflicts, meal scope and fail-closed evidence semantics.

Once professional NutritionPlan support existed, keeping both evaluators authoritative created a correctness risk. A meal could be blocked by Plan-Fit but still be ranked by recommendations, or a recommendation could reject a rule shape that Plan-Fit already understood.

Preference, availability, family ratings, diversity and feedback are useful ranking signals, but they must not override mandatory nutrition or safety rules.

## Decision

For a single-Person recommendation with an explicit meal type, Meal Plan-Fit is the authoritative nutrition/safety evaluator.

The pipeline is:

```text
candidate + final portion
-> Meal Plan-Fit
-> mandatory eligibility gate
-> Plan-Fit score when available
-> user preference / advisory reaction ranking
-> practical availability/context
-> family preference
-> diversity
-> feedback learning
```

In practical recommendation flows, optional automatic portion sizing happens before Meal Plan-Fit. The evidence therefore evaluates the exact portion that is later ranked.

### Eligibility

A candidate with `MealPlanFitRead.eligible == false` remains ineligible. Preference, family ratings, practical ranking, diversity and feedback cannot turn it back into an eligible recommendation.

Plan-Fit exclusion evidence is exposed in recommendation exclusion reasons so persisted recommendation runs remain auditable.

### Scoring

When `MealPlanFitRead.fit_score` is available, recommendation scoring uses it as the nutrition-fit component.

Legacy recommendation energy/nutrient scores are not added on top of Plan-Fit in this mode. Doing so would recreate a second nutrition interpretation and double-count evidence.

If Plan-Fit is eligible but has no numeric `fit_score`, the nutrition score component is omitted. It is not silently converted to zero. Non-nutrition ranking signals may still order otherwise eligible candidates.

### Preference and advisory reactions

User preference and advisory reaction effects remain separate recommendation signals. They are applied only after Plan-Fit eligibility has been established.

### Practical recommendation

Home/pantry/commercial availability remains a distinct practical layer. The current implementation computes Plan-Fit for the final candidate portions, then applies practical exclusions and later ranking signals.

### Backward-compatible unscoped calls

`MealPlanFitCreate` currently requires an explicit `meal_type`. Existing recommendation API calls where `meal_type` is omitted therefore keep the legacy evaluator temporarily.

This fallback is explicit in persisted recommendation context and must not be treated as equivalent to the scoped Plan-Fit path.

### Shared-family recommendations

Shared-family recommendation still uses the legacy participant evaluator in this slice. Each participant can have a different portion and EffectiveNutritionPlan, so shared Plan-Fit integration requires participant-specific Plan-Fit evidence to be carried into the shared ranking model.

That extension is deferred rather than approximated.

## Consequences

Positive:

- professional NutritionPlan rules and recommendation eligibility use one authority;
- meal-scoped mandatory minimums/ranges no longer fail simply because the legacy recommendation evaluator did not support their shape;
- preference cannot outrank a mandatory plan failure;
- auto-sized practical candidates are evaluated at their actual final portion;
- persisted engine/context metadata identifies Plan-Fit recommendation runs;
- unknown/unscored Plan-Fit evidence is not represented as a fake zero.

Trade-offs:

- scoped recommendation currently evaluates Plan-Fit once per candidate, which is correct but not yet optimized for large candidate sets;
- the existing private candidate-loader dependency from MealPlanFit remains technical debt;
- unscoped and shared-family recommendation still have legacy nutrition evaluation paths pending explicit contracts/refactoring.

## Follow-up

- move shared candidate loading into a public common service rather than private recommendation API helpers;
- add participant-specific Plan-Fit to shared-family recommendation;
- decide whether unscoped recommendation should be removed or gain an explicit non-meal Plan-Fit contract;
- optimize batch Plan-Fit compilation/evaluation without changing semantics;
- extend the same common evaluator to restaurant/delivery discovery rather than creating provider-specific nutrition logic.
