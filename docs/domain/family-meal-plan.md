# Family meal plan

## Purpose

The Family meal plan is the operational centre of NutriFlow. It answers what the Family plans to eat and allows that plan to be changed before the meal becomes historical intake.

## Four fixed meal types

NutriFlow uses exactly four normal meal types:

```text
breakfast  Pequeno-almoço
lunch      Almoço
snack      Lanche
dinner     Jantar
```

The shared `MealType` contract is used by the meal-plan API and the existing recommendation request APIs. Arbitrary values such as `brunch` are rejected at the server boundary.

## Read model

```text
GET /api/families/{family_id}/meal-plan?start_date=YYYY-MM-DD&days=1..14
```

The response uses Family-local calendar dates and always returns all four slots for every requested day, even when a slot is empty.

A slot may contain more than one MealEvent so split-Family situations remain representable, but the normal UI optimises for one shared meal.

## Write model

```text
POST   /api/families/{family_id}/meal-plan
PATCH  /api/families/{family_id}/meal-plan/{meal_event_id}
DELETE /api/families/{family_id}/meal-plan/{meal_event_id}
```

A planned entry contains:

- local date and time;
- one of the four fixed meal types;
- a Family Recipe;
- one or more Family participants;
- optional Person-specific quantities/units;
- optional location and notes.

Only `planned` MealEvents are mutable through this planning API. Prepared, served and completed events are historical/lifecycle evidence and are not edited as if they were still plans.

`DELETE` changes a planned MealEvent to `cancelled`; it does not destroy history.

## Person-specific portions

A shared meal remains one MealEvent. Each selected Person receives one MealParticipant and a Recipe Serving.

When no explicit quantity is supplied, the default portion is derived from Recipe yield/serving-count evidence:

- yield + serving count -> `yield / serving_count`;
- serving count without yield -> one `serving`;
- yield without serving count -> whole yield;
- neither -> one `recipe`.

When a current RecipeCompositionSnapshot exists, the existing deterministic Serving nutrition calculator scales that snapshot to each Person's planned quantity. Unsafe conversions fail rather than guessing density or portion meaning.

## Web UX

`Refeições` is now a planner rather than a read-only agenda.

`Hoje` and `Semana` show the same four slots. Empty slots contain an explicit add action. Planned entries can be edited or removed. The editor selects Recipe, time/location, participants and optional individual portions.

The existing recommendation workflow remains available under `Recomendar`, but it is a supporting tool rather than the primary meal screen.

## Next integration

The next large functional block should connect this plan to household inventory:

```text
planned Recipe quantities
-> ingredient requirements
-> subtract Pantry stock
-> Shopping requirements
-> durable ShoppingList
```
