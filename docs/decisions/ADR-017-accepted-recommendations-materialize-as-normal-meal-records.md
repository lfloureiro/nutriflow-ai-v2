# ADR-017: Accepted recommendations materialize as normal meal records

## Status

Accepted.

## Context

NutriFlow now persists recommendation runs, candidate options and immutable accept/reject/modify feedback events.

The planner still needs an authoritative representation of what is actually scheduled. Reusing recommendation records themselves as the meal plan would mix decision history with operational meal state and make later served/consumed tracking awkward.

## Decision

An accepted or modified eligible recommendation is materialized as the existing meal-domain records:

- `MealEvent` for the eating occasion;
- `MealParticipant` for the Person;
- `Serving` for the planned food or recipe portion.

The associated `MealRecommendationFeedback` references the resulting `Serving`.

The `Serving` is recalculated from the exact versioned Food or Recipe composition snapshot persisted on the recommendation option.

An `accepted` action must keep the recommended quantity and unit. Quantity or unit changes are recorded as `modified`.

Rejected or ineligible options do not materialize meal records through this service.

## Consequences

Recommendation history remains immutable and explainable while the normal meal domain remains the authoritative source for planned, served and consumed intake.

Daily nutrition aggregation can continue to depend on Serving history without needing recommendation-specific branches.

Exact composition provenance is retained from recommendation through planned Serving.

The current increment does not solve retry idempotency, later replacement of an already-created plan, shared-family optimization or automatic daily-state recomputation. Those remain separate concerns.
