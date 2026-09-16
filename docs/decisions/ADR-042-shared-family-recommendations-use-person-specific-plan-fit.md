# ADR-042 — Shared-family recommendations use Person-specific Meal Plan-Fit

## Status

Accepted.

## Context

ADR-041 made Meal Plan-Fit the authoritative nutrition and safety evaluator for meal-scoped single-Person recommendations, but deliberately left shared-family recommendations on the legacy participant evaluator.

A shared meal is one common candidate with Person-specific portions. Each participant may also have a different active NutritionPlan, DailyNutritionState, mandatory constraints, adverse reactions and preferences. Applying one participant's nutrition evaluation to the group would therefore be incorrect.

The existing shared recommendation contract already aggregates participant evaluations by protecting the worst-served participant: a candidate is eligible only when every participant is eligible, and group ranking considers the minimum participant score before the average score.

## Decision

Shared practical recommendations with an explicit meal type evaluate Meal Plan-Fit independently for every `Person × candidate × final portion`.

The pipeline is:

```text
common candidate
-> Person-specific portion
-> that Person's EffectiveNutritionPlan + DailyNutritionState
-> Meal Plan-Fit
-> Person-specific mandatory eligibility gate
-> Person preference / advisory reaction
-> Person practical context
-> shared eligibility aggregation
-> minimum score before average score
-> diversity
-> feedback
```

### Person isolation

Each participant's Plan-Fit is compiled from that participant's own persisted nutrition context. A professional rule for Person A is never copied to Person B.

Plan-Fit is calculated against the exact Person-specific portion that enters the shared recommendation. Optional portion sizing therefore occurs before Plan-Fit.

### Shared eligibility

A shared candidate is eligible only if every participant evaluation is eligible.

If one participant fails a mandatory Plan-Fit rule, has a mandatory conflict, or otherwise becomes Plan-Fit-ineligible, preference, diversity, feedback and the other participants' scores cannot make the shared candidate eligible.

Participant-specific exclusion reasons retain the Person id so the group decision remains explainable and auditable.

### Shared ranking

For eligible candidates, the existing shared-family fairness rule remains unchanged:

1. higher minimum participant score first;
2. then higher average participant score;
3. then stable candidate-key ordering.

Plan-Fit therefore changes the nutrition authority, not the established group-ranking objective.

### Legacy service boundary

The lower-level legacy shared-family evaluator remains available temporarily for direct legacy/unit-test callers. The production shared-practical API uses the Plan-Fit-aware path.

This avoids an unrelated rewrite in the same change while keeping the operational endpoint on the authoritative evaluator.

## Consequences

Positive:

- professional NutritionPlan rules are enforced correctly inside shared meals;
- different family members can safely have different plans and portions;
- a mandatory failure for one participant cannot be averaged away by the group;
- existing practical, preference, diversity and feedback semantics remain layered after Plan-Fit;
- shared exclusion evidence identifies which Person caused the block;
- one common nutrition evaluator now covers scoped single-Person and shared-practical recommendation paths.

Trade-offs:

- Plan-Fit is currently evaluated per participant and candidate; this is correct but not yet optimized for large candidate sets;
- the Plan-Fit-aware shared service reuses private aggregation helpers from the legacy shared service;
- the direct lower-level legacy shared evaluator still exists and should not be treated as the authoritative production nutrition path.

## Follow-up

- extract shared candidate/aggregation helpers into a public common service;
- move MealPlanFit candidate loading out of private recommendation API helpers;
- consider removing or explicitly deprecating the legacy shared nutrition evaluator once all callers use Plan-Fit;
- extend the same evaluator to restaurant/delivery recommendation flows;
- optimize Plan-Fit compilation/evaluation batching without changing eligibility semantics.
