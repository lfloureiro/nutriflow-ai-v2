# Meal event and serving domain

## Purpose

NutriFlow must represent what is planned for a meal, who participates, what portion each person receives and what is actually consumed.

The model must support both individual and shared family meals without duplicating the meal itself for every Person.

The implemented meal domain is:

```text
Family
  -> MealEvent
       -> MealParticipant
            -> Serving
                 -> ServingNutritionComponent
```

A shared meal is one `MealEvent` with multiple `MealParticipant` records. An individual meal is the same structure with one participant.

There is intentionally no separate `SharedMeal` table.

---

## MealEvent

`MealEvent` represents one eating occasion in the Family context.

Examples:

- breakfast at home;
- an individual work lunch;
- a shared family dinner;
- a restaurant meal;
- a planned snack;
- a replacement meal after a previous plan changes.

Implemented fields include:

- `family_id`;
- `replaces_meal_event_id`;
- `meal_type`;
- `title`;
- `scheduled_at`;
- `timezone`;
- `status`;
- `served_at`;
- `completed_at`;
- `location`;
- `source`;
- `source_reference`;
- `notes`;
- timestamps.

The Family owns the shared context. Nutrition remains person-specific through participants and servings.

### Event lifecycle

Supported event statuses are:

- `planned`;
- `prepared`;
- `served`;
- `completed`;
- `cancelled`;
- `replaced`.

The event lifecycle describes the shared meal occasion, not whether every participant ate the same amount or even ate at all.

Participant-specific outcome belongs to `MealParticipant` and actual intake belongs to `Serving`.

### Replacement history

`replaces_meal_event_id` allows a new event to preserve the fact that it replaced an earlier plan.

The previous event is not overwritten. This keeps planning history explainable and supports later analysis of adherence and substitutions.

---

## MealParticipant

`MealParticipant` associates one Person with one MealEvent.

A Person may occur only once as a participant in the same event.

Implemented fields include:

- `meal_event_id`;
- `person_id`;
- `status`;
- `notes`;
- timestamps.

Supported participant statuses are:

- `planned`;
- `served`;
- `consumed`;
- `partial`;
- `skipped`;
- `replaced`.

This distinction matters because one shared family dinner can have different outcomes for different people.

Example:

```text
Family dinner
  Person A -> consumed
  Person B -> partial
  Person C -> skipped
```

A participant is the integrity boundary between a Person and their servings for that event.

Application services must ensure that participants belong to the same Family as the MealEvent.

---

## Serving

`Serving` is the person-specific portion of one item within a MealEvent.

It belongs to a `MealParticipant`, which determines both the Person and MealEvent.

This prevents the database from storing inconsistent combinations such as a serving linked to one event but to a participant from another event.

One participant may have multiple servings in a meal.

Example:

```text
Dinner
  Person A
    -> spaghetti bolognese
    -> salad
    -> fruit
```

Implemented serving fields include:

- `meal_participant_id`;
- optional `food_item_id`;
- optional `recipe_id`;
- `item_type`;
- `item_key`;
- `item_name`;
- `status`;
- planned, served and consumed quantity;
- `quantity_unit`;
- planned, served and consumed energy;
- `nutrition_source`;
- `source_reference`;
- `consumed_at`;
- `notes`;
- timestamps.

At most one direct catalogue reference may be populated: FoodItem or Recipe.

### Serving lifecycle

Supported statuses are:

- `planned`;
- `served`;
- `consumed`;
- `partial`;
- `skipped`;
- `replaced`.

The status is retained even when quantities are available because zero or missing intake has different meanings depending on whether food has not yet been eaten, was skipped or was replaced.

### Planned, served and consumed quantities

NutriFlow keeps the stages separate.

Example:

```text
planned:   350 g
served:    350 g
consumed:  300 g
```

This supports:

- meal planning;
- portion preparation;
- partial consumption;
- adherence analysis;
- later recalculation of DailyNutritionState.

Consumed quantity may not exceed served quantity when both are known.

The served amount may exceed the planned amount. Actual behaviour must not be discarded simply because it differs from the plan.

---

## ServingNutritionComponent

Energy is stored directly on Serving for frequent daily calculations.

Other nutritional values are represented by extensible `ServingNutritionComponent` records.

Implemented fields include:

- `serving_id`;
- `nutrient_key`;
- `planned_value`;
- `served_value`;
- `consumed_value`;
- `unit`;
- timestamps.

Examples of `nutrient_key` include:

- `protein`;
- `carbohydrate`;
- `fat`;
- `fibre`;
- `sodium`;
- future nutrients with a justified planning use case.

Only one record for a nutrient key is allowed per Serving.

---

## Food and recipe references

The Food/Recipe catalogue is now implemented as a separate domain layer.

Serving may reference:

- a `FoodItem`; or
- a `Recipe`.

The catalogue relationship is optional because historical/manual/external meals may exist without a native catalogue record.

Catalogue foreign keys use `ON DELETE SET NULL`, preserving the meal even if a referenced catalogue record is later removed.

The Serving still stores:

- item type;
- item key;
- item name;
- quantity snapshots;
- energy snapshots;
- ServingNutritionComponent snapshots;
- nutrition source/reference.

These values describe the meal as it was planned/served/consumed. They are not dynamically read from the current Food/Recipe record.

Therefore later catalogue edits or composition corrections cannot silently rewrite historical intake.

Detailed catalogue semantics are documented in `docs/domain/food-catalog-model.md` and ADR-013.

---

## Shared meal example

```text
MealEvent: family dinner - spaghetti bolognese

MealParticipant: Person A
  Serving -> Recipe: spaghetti bolognese
    planned quantity: 350 g
    consumed quantity: 300 g
    consumed energy: 560 kcal
    protein consumed: 27.5 g

MealParticipant: Person B
  Serving -> Recipe: spaghetti bolognese
    planned quantity: 250 g
    consumed quantity: 250 g
    consumed energy: 465 kcal
    protein consumed: 23 g
```

The family shares the eating occasion and recipe context, while portions and nutrition remain individual.

---

## Shared-family recommendation semantics

The recommendation layer now mirrors this same separation.

A shared-family candidate uses one common FoodItem or Recipe identity, while every Person receives an explicit portion and is evaluated independently against their own:

- DailyNutritionState;
- mandatory reactions and constraints;
- preferences;
- practical and schedule context.

A shared candidate is eligible only if every participant is individually eligible. Family-level ranking cannot override a Person's hard exclusion.

Eligible shared candidates are ranked fairness-first by the minimum participant score and then by the average participant score.

This optimization layer does not introduce a SharedMeal persistence table. Accepted shared recommendations can be materialized later using the existing one-MealEvent/multiple-MealParticipant structure.

Detailed semantics are documented in `docs/domain/shared-family-meal-optimization.md` and ADR-020.

---

## Relationship to DailyNutritionState

MealEvent, MealParticipant, Serving and ServingNutritionComponent are authoritative planning/intake records.

`DailyNutritionState` is derived from them together with the person's NutritionTarget.

Conceptually:

```text
NutritionTarget
+ planned Servings
+ consumed Servings
-> DailyNutritionState
```

A future family dinner can therefore influence recommendations made earlier in the day because its planned servings contribute to the person's planned nutrition state.

DailyNutritionState may be recalculated. Historical serving records must not be replaced by the derived state.

---

## Next layer

The next meal-domain increments are:

1. materialize an accepted shared recommendation into one MealEvent with multiple MealParticipants and person-specific Servings;
2. add replacement and idempotency semantics for plan edits and API retries;
3. add restaurant/delivery, pantry and shopping context;
4. persist family-level recommendation audit history when its ownership semantics are explicit.
