# ADR-019 — Practical context filters before nutrition ranking

## Status

Accepted.

## Context

NutriFlow already ranks meal candidates using deterministic safety, nutrition and preference rules. A nutritionally suitable candidate can still be unusable when the Person is unavailable, is at an incompatible location, lacks preparation time or lacks required kitchen facilities.

ScheduleEntry already stores recurring and one-off planning context, but the recommendation engine did not yet consume it.

Practical metadata is also incomplete today. Persisting preparation/location capability directly on FoodItem or Recipe before restaurant, delivery and pantry domains are designed would prematurely constrain the catalogue model.

## Decision

Add a deterministic practical-context wrapper around the existing meal recommendation service.

The wrapper:

- evaluates the requested timezone-aware meal instant against ScheduleEntry records;
- gives matching one-off availability effects precedence over recurring effects;
- excludes all candidates when the effective schedule is unavailable;
- supports request-specific location, available preparation time and kitchen availability;
- accepts non-persisted CandidatePracticalProfile inputs for candidate-specific feasibility;
- excludes practically impossible candidates before passing the rest to the existing safety/nutrition ranking service;
- preserves explicit practical exclusion reasons and explanations in RecommendationResult;
- raises rather than silently ignoring recurrence rules outside its supported subset.

The supported recurrence subset is intentionally conservative: DAILY/WEEKLY, optional BYDAY, and INTERVAL=1.

## Consequences

The recommendation flow now distinguishes three responsibilities:

1. practical feasibility for the requested context;
2. mandatory food-safety/nutrition eligibility;
3. deterministic nutrition/preference ranking.

Existing FoodItem/Recipe schema does not change.

Recommendation history can already persist practical exclusion reasons and explanations without new tables.

A later domain increment may persist preparation, restaurant, delivery or pantry feasibility metadata once those concepts have stable semantics.

Full RFC 5545 recurrence evaluation is not claimed by this increment. Unsupported recurrence rules fail explicitly so schedule context is never silently misinterpreted.

## Alternatives rejected

### Put preparation/location fields directly on FoodItem and Recipe now

Rejected because practical feasibility may belong to a recipe, household, restaurant offer, delivery offer or pantry state rather than the canonical food identity.

### Treat practical constraints only as ranking penalties

Rejected because a meal that cannot be prepared or obtained in the current context should not remain an eligible recommendation merely with a lower score.

### Ignore recurrence rules that are not understood

Rejected because silently omitting a blocking or preferred schedule occurrence could produce incorrect planning behaviour.
