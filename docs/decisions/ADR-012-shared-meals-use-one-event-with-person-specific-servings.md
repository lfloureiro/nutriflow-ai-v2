# ADR-012: Shared meals use one event with person-specific servings

- Status: Accepted
- Date: 2026-08-21

## Context

NutriFlow plans nutrition for individuals while many eating occasions are shared by a family.

A family dinner may be one cooking and scheduling event, but each Person can have:

- a different portion;
- different nutrient totals;
- a different participation outcome;
- a different amount actually consumed.

The model must avoid both extremes:

1. duplicating the same shared meal once per Person; or
2. storing only one family-level quantity that cannot represent individual nutrition.

The system must also preserve the difference between planned, served and consumed intake because this is required for DailyNutritionState and later adaptive planning.

## Decision

A shared or individual eating occasion is represented by a single `MealEvent`.

`MealEvent` belongs to a Family.

People participate through `MealParticipant`.

Person-specific food portions are represented by `Serving` records owned by a MealParticipant.

Nutrient-level values beyond energy are represented by `ServingNutritionComponent`.

The relationship is:

```text
Family
  -> MealEvent
       -> MealParticipant -> Person
            -> Serving
                 -> ServingNutritionComponent
```

There is no separate `SharedMeal` entity.

A MealEvent with multiple participants is a shared meal. A MealEvent with one participant is an individual meal.

## Lifecycle separation

MealEvent lifecycle describes the eating occasion:

- planned;
- prepared;
- served;
- completed;
- cancelled;
- replaced.

MealParticipant and Serving lifecycle describes person-specific outcomes:

- planned;
- served;
- consumed;
- partial;
- skipped;
- replaced.

These lifecycle layers must not be collapsed into one status because a shared meal may be completed while one participant skipped it and another consumed only part of their serving.

## Portion representation

Serving stores separate planned, served and consumed quantities and energy values.

This allows NutriFlow to retain both intent and observed behaviour.

Actual values may differ from planned values without rewriting history.

## Nutrition data

Serving contains direct energy fields because energy is a frequent daily calculation input.

Other nutrients are extensible child records so the domain is not limited to a fixed macro set.

The future Food/Recipe catalogue will provide composition and references, but historical Serving records remain the authoritative record of what was planned, served or consumed at that time.

## Consequences

### Positive

- one shared meal is not duplicated across people;
- portions remain person-specific;
- planned versus actual intake is preserved;
- partial consumption and skipped meals are representable;
- DailyNutritionState can aggregate person-specific servings;
- the model supports one meal containing several dishes/items;
- future recipe, restaurant and food catalogue records can be linked without redesigning the meal lifecycle.

### Trade-offs

- queries for a Person's servings go through MealParticipant;
- services must ensure a participant belongs to the same Family as the MealEvent;
- nutrition snapshots require explicit synchronization logic when a planned serving changes before consumption;
- Food/Recipe catalogue identity is intentionally deferred to a later domain increment.

## Rejected alternatives

### One MealEvent per Person

Rejected because it duplicates shared context and makes family-level planning, preparation and replacement harder to reason about.

### One family-level Serving

Rejected because nutrition targets and actual intake are person-specific.

### Separate SharedMeal and IndividualMeal entities

Rejected because both are the same eating-occasion concept. Participant count is sufficient to distinguish shared and individual contexts.

### Serving linked independently to MealEvent and Person

Rejected because duplicated foreign keys could produce inconsistent event/person combinations. Serving instead belongs to MealParticipant, which already establishes both identities.
