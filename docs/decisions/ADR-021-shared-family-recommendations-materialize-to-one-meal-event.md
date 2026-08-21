# ADR-021: Shared-family recommendations materialize to one MealEvent

## Status

Accepted.

## Context

Shared-family recommendation evaluates one common Food or Recipe for several Persons while keeping quantity, nutrition state, preferences, mandatory constraints and practical context person-specific.

When a family accepts such a proposal, persistence must preserve both facts:

1. there was one shared eating occasion;
2. every Person had an individual planned portion and nutritional impact.

Creating one MealEvent per Person would duplicate the shared occasion and make later family-level replacement, scheduling and audit semantics harder to reason about.

Creating one family-level Serving would lose person-specific portion and nutrition information.

## Decision

An accepted eligible shared-family recommendation materializes as:

```text
one MealEvent
  -> one MealParticipant per Person
       -> one person-specific Serving per participant
```

No new SharedMeal table is introduced.

The materialization service requires persisted Persons and persisted versioned Food/Recipe composition snapshots. It reloads those records before creating the authoritative plan and rejects missing or inconsistent references.

The recommended quantity and unit for each Person are preserved exactly. Planned Serving energy and nutrients are recalculated through the existing serving-nutrition service using the persisted composition snapshot used by the recommendation.

An ineligible shared-family recommendation, or a result in which any participant evaluation is ineligible or inconsistent with the selected common candidate, cannot be materialized.

## Consequences

Positive consequences:

- shared context remains normalized in one MealEvent;
- nutrition remains person-specific;
- DailyNutritionState recalculation can consume normal Serving history without special family-meal logic;
- the existing meal lifecycle and replacement model remain reusable;
- exact Food/Recipe composition provenance is preserved;
- recommendation safety decisions cannot be bypassed during materialization.

Trade-offs:

- family-level recommendation acceptance is not yet persisted as its own feedback entity;
- modifications to one Person's recommended portion need explicit future semantics;
- retries need a future idempotency/replacement layer to prevent duplicate MealEvents.

## Alternatives rejected

### One MealEvent per Person

Rejected because it duplicates one real shared occasion and fragments family planning history.

### One family-level Serving

Rejected because it cannot represent individual portions, nutrient impact or consumption outcomes.

### New SharedMeal persistence aggregate

Rejected for now because MealEvent + MealParticipant + Serving already expresses the required persistence semantics without another parallel meal hierarchy.
