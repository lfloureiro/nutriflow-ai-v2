# ADR-018 — DailyNutritionState is recalculated from Serving history

## Status

Accepted

## Context

NutriFlow now has authoritative planned and actual meal records (`MealEvent`, `MealParticipant`, `Serving`) and a derived `DailyNutritionState` consumed by recommendation logic.

Without one deterministic aggregation policy, planned and consumed values could be double-counted, cancelled/replaced meals could remain in state, timezone boundaries could differ between callers, and state snapshots could drift away from their source history.

## Decision

`DailyNutritionState` is recalculated from authoritative Serving history for one Person and one explicit local calendar date.

The calculation:

- uses an explicit IANA timezone to create the local day boundary;
- excludes cancelled/replaced MealEvents, skipped/replaced participants and skipped/replaced Servings;
- treats consumed/partial or otherwise realized Servings as consumed only, never simultaneously planned;
- uses served values as the best remaining planned estimate for non-realized served portions;
- otherwise uses planned values;
- applies an explicitly supplied NutritionTarget only when it belongs to the Person and is valid on that date;
- converts nutrient values only through the existing safe unit-conversion rules;
- fails rather than silently undercounting when a required nutrient conversion is unsafe;
- updates the existing derived state when the same calculation version is recomputed;
- preserves a separate state when the calculation version changes;
- records source-window and Serving lineage metadata in `calculation_inputs`.

The service does not mutate or replace the authoritative MealEvent/Serving history.

## Consequences

Recommendation logic can consume a compact state that is reproducible from source records.

A Serving that becomes consumed stops contributing its old planned amount, avoiding double counting.

Local calendar semantics remain stable around UTC day boundaries and daylight-saving changes.

Historical algorithm semantics remain available through calculation-version changes while routine recomputation of one algorithm does not create duplicate state rows.

Automatic target selection, adherence/confidence scoring and event-driven refresh remain separate concerns.
