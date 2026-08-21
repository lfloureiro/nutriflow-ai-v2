# Shared family meal materialization

## Purpose

Shared-family recommendation chooses one common Food/Recipe candidate while keeping nutrition and portions person-specific.

Materialization converts an accepted eligible shared-family recommendation into the authoritative meal domain without duplicating the shared eating occasion.

The resulting structure is:

```text
SharedFamilyMealRecommendationResult
  -> selected eligible shared candidate
       -> one MealEvent
            -> MealParticipant for Person A -> Serving with A's portion
            -> MealParticipant for Person B -> Serving with B's portion
            -> ...
```

There is still no separate `SharedMeal` persistence entity.

## Service

`materialize_shared_family_recommendation` accepts:

- one `SharedFamilyMealRecommendationResult`;
- the selected `candidate_key`;
- timezone-aware `scheduled_at`;
- explicit timezone;
- meal type;
- optional title, location and notes;
- Serving nutrition calculation version.

The selected recommendation must exist exactly once, be eligible and have a family rank.

## One shared event, individual portions

The service creates exactly one `MealEvent` in `planned` state.

For every participant evaluation it creates:

- one `MealParticipant` in `planned` state;
- one `Serving` in `planned` state;
- the exact quantity and unit recommended for that Person;
- planned energy and nutrients calculated from the exact persisted composition snapshot used by the recommendation.

The common item identity is shared conceptually, but the Serving records remain person-specific because portions and nutritional impact differ by Person.

## Persistence boundary

Materialization deliberately requires persisted Persons and persisted Food/Recipe composition snapshots.

This prevents an accepted recommendation from silently inserting transient catalogue objects while creating a meal.

Before writing the plan the service reloads:

- every Person by ID;
- every FoodCompositionSnapshot or RecipeCompositionSnapshot by ID.

It then verifies that the persisted catalogue identity still matches the selected shared candidate.

## Family integrity

All materialized participants must belong to the same Family.

A Family-specific FoodItem or Recipe must belong to that same Family. Global catalogue entries remain usable by any Family.

The MealEvent is linked to that single Family.

## Safety and recommendation integrity

Materialization does not re-rank candidates and does not turn an excluded candidate into an accepted plan.

The service requires:

- the shared candidate itself to be eligible;
- every participant evaluation to be eligible;
- participant candidate identity to match the selected shared candidate;
- each participant candidate quantity/unit to match the recommended SharedMealPortion;
- exactly one Food or Recipe composition per participant candidate.

If any of these invariants fail, no planned shared meal is produced.

Mandatory allergy, nutrition and practical-context rules therefore remain decisions of the recommendation layer and cannot be bypassed by the materialization service.

## Nutrition snapshots

Serving nutrition is recalculated through the existing `calculate_serving_nutrition` service instead of copying display JSON or aggregate family scores.

This preserves the existing rules for:

- Decimal arithmetic;
- safe unit conversion;
- exact composition provenance;
- planned energy;
- planned nutrient components.

The resulting Serving snapshots become authoritative planned-intake records and can feed the next DailyNutritionState recalculation.

## Provenance

Generated MealEvent and Serving records use recommendation provenance and store a source reference derived from the shared-family recommendation engine version.

This is not yet a persisted shared-family recommendation/feedback history. A later increment may add a durable family-level decision record if product requirements justify it.

## Non-goals

This increment does not yet implement:

- per-person modifications after accepting the family proposal;
- idempotency keys for API retries;
- replacement of an already-materialized family meal;
- persisted family-level accepted/rejected feedback;
- pantry or shopping reservation;
- restaurant ordering.

Those concerns remain separate from the basic authoritative meal materialization step.
