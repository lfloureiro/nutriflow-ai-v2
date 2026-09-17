# ADR-049 — Shared-family weekly planning reuses Person-specific weekly planning

Status: Accepted

## Context

Phase 8c now has a deterministic one-Person multi-slot optimizer that consumes existing recommendation and Meal Plan-Fit evidence. It rechecks combination-level mandatory weekly maxima and same-day mandatory nutrient upper bounds, and it ranks feasible combinations using confirmed weekly minimum support before existing score/diversity criteria.

A Family meal is still one shared candidate with Person-specific portions and Person-specific Meal Plan-Fit evidence. Extending week-level planning to shared meals must not collapse those independent nutrition states into a synthetic Family nutrition state.

## Decision

The shared-family multi-slot planner operates over already-evaluated shared candidates. Each shared candidate contains:

- the shared `SharedMealCandidateEvaluation`;
- one participant evaluation per Person using that Person's exact portion;
- exactly one `MealPlanFitRead` per participant for the same slot and candidate.

For every candidate combination across the requested week, the shared planner projects the chosen shared meals back into one singleton-candidate weekly plan per Person and calls the existing `optimize_weekly_slots()` service.

Therefore the Person planner remains the sole owner of:

- mandatory weekly maximum recomposition;
- lower-bound / unknown weekly-frequency safety;
- same-day mandatory nutrient upper-bound recomposition;
- confirmed mandatory/advisory weekly minimum support;
- Person-specific candidate score aggregation.

The shared layer does not recalculate NutritionPlan rules, DailyNutritionState values, food classification or weekly frequency progress.

A shared combination is feasible only when every participant's Person-specific weekly projection is feasible.

## Family-level ranking

Among feasible shared combinations, ordering is deterministic:

1. number of participants receiving confirmed mandatory weekly-minimum support;
2. total confirmed mandatory supported occurrences;
3. number of participants receiving confirmed advisory weekly-minimum support;
4. total confirmed advisory supported occurrences;
5. minimum participant score across the proposed week;
6. average participant score;
7. repeated shared-candidate count;
8. stable candidate-key sequence.

This extends the existing shared-meal fairness rule without placing weekly support inside the numeric recommendation score.

## Safety and uncertainty

A mandatory failure for one participant blocks the shared combination for the Family. Support for another participant can never rescue it.

Missing or inconsistent Person-specific Plan-Fit evidence is not treated as zero. Structural mismatches raise a deterministic planning error; mandatory uncertainty handled by the Person planner continues to fail closed.

## Search scope

The v1 shared-family optimizer remains in-memory and exhaustively enumerated under the same explicit combination cap used by the one-Person planner. It refuses a larger search space instead of silently switching to an approximate algorithm.

## Persistence

No new persistence is introduced. There is no migration. Alembic head remains `d2e6f1a9c4b7`.

## Consequences

The implementation intentionally composes existing authoritative layers rather than introducing a second weekly evaluator. The next increments may add API orchestration, richer across-week category/protein diversity, pantry/shopping/schedule coupling and eventually a scalable search strategy, while preserving this Person-specific safety boundary.
