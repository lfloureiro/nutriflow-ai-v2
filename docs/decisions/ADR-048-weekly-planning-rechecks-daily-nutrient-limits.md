# ADR-048 — Weekly planning rechecks daily nutrient limits across same-day slots

Status: Accepted

## Context

ADR-047 introduced deterministic one-Person multi-slot weekly composition over existing recommendation and Meal Plan-Fit evidence.

A candidate evaluated alone against a `DailyNutritionState` may be safe even when two or more individually safe candidates selected for the same date are unsafe together. For example, with 30 g already planned/consumed and a mandatory 100 g daily maximum, two candidates adding 40 g each individually project to 70 g, but the combined proposal projects to 110 g.

The weekly planner must not introduce another nutrition evaluator. Meal Plan-Fit remains authoritative for rule interpretation, unit conversion, Person-specific context and candidate evidence.

## Decision

The weekly multi-slot planner may recompose **mandatory daily upper-bound safety** from the structured `MealPlanFitRuleRead` evidence already emitted by Meal Plan-Fit.

For selected choices sharing the same `planning_date` and daily nutrient `rule_id`:

1. the candidate contribution is `observed_value`;
2. the common pre-candidate daily baseline is reconstructed as `projected_daily_value - observed_value`;
3. every candidate for that rule/date must imply the same baseline;
4. the combination projection is `baseline + sum(candidate contributions)`;
5. mandatory irreversible upper bounds are rechecked against that combined projection.

The combined hard check currently covers:

- maximum operators (`max`, `lte`, `<=`, `<`);
- the upper bound of a `range` rule;
- overshooting an exact `target` rule.

A daily minimum is not turned into a whole-day hard failure in this increment because the planner input may represent only a subset of that day's remaining meal slots. Minimums can still be satisfied by later/unrepresented meals. This preserves the existing Meal Plan-Fit rule that a candidate moving toward a daily minimum can be `support` rather than an immediate failure.

## Safety and consistency rules

- Daily values are coupled **per Person, per date, per rule**; values from different dates are never summed together.
- The planner does not reload `DailyNutritionState`, reinterpret NutritionPlan rules, convert units, or recalculate candidate nutrition.
- Missing mandatory evidence needed to prove a combined upper bound safe fails closed.
- Inconsistent operator, target/unit metadata or reconstructed daily baselines are treated as planning errors rather than guessed or averaged.
- Candidate-level and meal-level mandatory Plan-Fit failures remain authoritative before combination evaluation.
- Weekly-frequency maximum checks from ADR-047 remain independent and are evaluated before daily coupling.

## Result shape

The in-memory weekly result records `rejected_by_mandatory_daily_limit` separately from `rejected_by_mandatory_weekly_maximum` so callers can explain why combinations were rejected.

The engine version advances to `weekly-multi-slot-v2`.

## Consequences

The Phase 8c planner can now detect a class of unsafe combinations that no single-slot Meal Plan-Fit evaluation can detect by itself, while preserving the existing Plan-Fit evaluation boundary.

This increment does not yet:

- force daily minimum completion when not all daily slots are represented;
- optimize closeness to daily nutrient targets as a new ranking dimension;
- optimize several Persons jointly;
- couple pantry, shopping or schedules;
- persist or accept a weekly proposal.

No schema migration is required. Alembic head remains `d2e6f1a9c4b7`.
