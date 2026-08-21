# ADR-016 — Recommendation feedback is an immutable event history

## Status

Accepted.

## Context

NutriFlow needs to learn whether a recommendation was accepted, rejected or modified. That feedback is useful for future heuristic and ML ranking, but it must not weaken deterministic safety and nutrition rules.

Recommendation output is also time-sensitive. Catalogue composition, DailyNutritionState, constraints, preferences and ranking algorithms may all change after a recommendation was shown. Persisting only the final chosen meal would lose the alternatives, scores and explanations that the user actually saw.

## Decision

Persist recommendation history in three layers:

1. `MealRecommendationRun` records one person-scoped recommendation execution, its planning date, engine version and optional DailyNutritionState/context reference.
2. `MealRecommendationOption` snapshots every evaluated candidate, including eligibility, rank, score breakdown, exclusion reasons, candidate subjects and nutrition values used at recommendation time.
3. `MealRecommendationFeedback` appends user/system feedback events with action `accepted`, `rejected` or `modified`, optionally linked to the resulting Serving.

Feedback is append-only event history. A later action does not overwrite an earlier one.

Catalogue and composition foreign keys are retained for traceability but use `ON DELETE SET NULL`; the option also stores stable candidate identity and a nutrition snapshot so historical recommendations remain interpretable after catalogue cleanup.

Feedback may only be attached to options that were eligible for presentation. Excluded candidates remain part of the recommendation audit trail but are not treated as user choices.

Learned ranking may consume this feedback in the future, but it remains downstream of mandatory safety and nutrition rules. ML or preference learning cannot make an ineligible option eligible.

## Consequences

Positive:

- recommendation decisions remain explainable after algorithms or catalogue data change;
- accept/reject/modify behaviour can be measured without reconstructing historical state;
- modifications can link to the resulting Serving and therefore to actual intake;
- future learned ranking has explicit, person-scoped training signals;
- safety exclusions remain auditable and outside the learning layer.

Trade-offs:

- recommendation history adds storage volume;
- snapshot JSON intentionally duplicates some derived values;
- repeated feedback events require consumers to define whether they need the full sequence or latest action;
- privacy/access control must treat recommendation history as person-scoped nutrition data.

## Follow-up

Subsequent increments should:

- materialize accepted/modified recommendations into planned MealEvent/Serving records through an application service;
- recalculate DailyNutritionState after planning/intake changes;
- expose recommendation history and feedback through authenticated API contracts;
- add learned ranking only after deterministic eligibility remains authoritative.
