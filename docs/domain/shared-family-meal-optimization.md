# Shared family meal optimization

## Purpose

NutriFlow should be able to recommend one common meal for a Family without pretending that every Person has the same nutrition target, restrictions, preferences or portion size.

The shared object is the candidate meal identity. Eligibility and nutrition remain person-specific.

Conceptually:

```text
Shared candidate FoodItem/Recipe
  -> Person A portion -> Person A safety/nutrition/practical evaluation
  -> Person B portion -> Person B safety/nutrition/practical evaluation
  -> Person C portion -> Person C safety/nutrition/practical evaluation
  -> family-level eligibility and rank
```

This is consistent with the existing meal persistence model, where one `MealEvent` can later contain multiple `MealParticipant` records and person-specific `Serving` records.

## SharedMealCandidateProposal

A proposal references exactly one versioned `FoodCompositionSnapshot` or `RecipeCompositionSnapshot` and contains exactly one `SharedMealPortion` for every participating Person.

Each portion stores:

- `person_id`;
- quantity;
- quantity unit.

Different people can therefore share the same dish while receiving different amounts.

A proposal is invalid if:

- it references both Food and Recipe composition, or neither;
- any participant is missing a portion;
- a participant has more than one portion;
- a quantity is zero or negative;
- a unit is empty;
- a Family-specific catalogue item belongs to another Family.

## Participant context

Each `SharedMealParticipantContext` contains:

- the Person;
- that Person's `DailyNutritionState`;
- preferences;
- adverse reactions;
- nutrition constraints;
- optional `PracticalMealContext`;
- optional candidate practical profiles.

The service requires at least two persisted Persons from the same Family and verifies that each DailyNutritionState belongs to the corresponding Person.

This prevents a family-level optimization from accidentally evaluating one person's portion against another person's state.

## Individual evaluation remains authoritative

For each proposal, NutriFlow builds a normal `MealCandidate` separately for each Person using that Person's portion.

The existing recommendation layers are then reused unchanged:

1. practical-context filtering when practical context is supplied;
2. mandatory adverse-reaction filtering;
3. mandatory nutrition-constraint filtering;
4. energy and nutrient fit;
5. preferences and advisory reactions.

No family-level score may make a candidate eligible when any Person's deterministic evaluation says it is ineligible.

Unsupported mandatory constraints and unsupported recurrence semantics continue to fail closed through the existing recommendation services.

## Shared eligibility

A shared candidate is eligible only when it is eligible for every participant.

If one Person has a mandatory allergy, an unavailable schedule window or another hard exclusion, the shared proposal is excluded even when it would otherwise score highly for the rest of the Family.

Exclusion reasons preserve the Person identity, for example:

```text
person:<person-id>:mandatory_reaction:ingredient:food:peanut
person:<person-id>:schedule_unavailable
```

This keeps family-level exclusion explainable.

## Fairness-first ranking

Eligible shared candidates are ranked deterministically using two person-level score summaries:

1. highest minimum participant score;
2. then highest average participant score;
3. then candidate key for deterministic tie-breaking.

The minimum score is considered before the average deliberately.

A candidate that is excellent for one Person but poor for another should not automatically outrank a candidate that works reasonably well for everyone merely because its arithmetic mean is high.

This first family-ranking policy is intentionally simple and explainable. It is versioned as `shared-family-meal-v1` and can evolve later without changing the rule that hard per-Person eligibility remains authoritative.

## Relationship to meal persistence

This increment recommends shared candidates but does not create meal records.

The intended next materialization shape is already supported by the meal domain:

```text
MealEvent: one shared dinner
  -> MealParticipant: Person A
       -> Serving: shared recipe, Person A quantity
  -> MealParticipant: Person B
       -> Serving: shared recipe, Person B quantity
```

There is still no need for a separate `SharedMeal` table.

## Persistence and history

This increment adds no database schema.

The current recommendation-history model remains person-scoped, so persisting one complete shared-family recommendation run as a first-class aggregate is intentionally deferred. The family optimizer is currently a deterministic orchestration service over existing person-level recommendation semantics.

Before family-level recommendation history is persisted, its audit shape should be designed explicitly rather than overloading `MealRecommendationRun` with ambiguous ownership.

## Future evolution

Likely next steps include:

- materializing an accepted shared proposal into one MealEvent with multiple MealParticipants and Servings;
- idempotency/replacement semantics for shared-plan edits;
- persisted family-level recommendation audit history;
- common-side-dish plus person-specific-main combinations;
- pantry, shopping and batch-cooking constraints;
- restaurant/delivery candidates that support participant-specific choices;
- richer fairness objectives only after they remain explainable and subordinate to hard per-Person rules.
