# NutriFlow AI v2 — Core meal-planning priorities

## Product correction

The primary value of NutriFlow is practical family meal planning. Health dashboards and individual analytics support that goal; they must not displace the workflows required to decide what the family will eat, maintain recipes, know what ingredients are available and prepare shopping requirements.

The core chain is:

```text
Ingredients
  -> Recipes
  -> Recipe nutrition
  -> Family meal plan
  -> Person-specific portions
  -> Pantry requirements
  -> Shopping requirements
  -> Meal history / feedback
```

## Four normal meal slots

Normal family planning uses exactly four meal types:

1. `breakfast` — Pequeno-almoço
2. `lunch` — Almoço
3. `snack` — Lanche
4. `dinner` — Jantar

These must become backend/domain-valid values, not arbitrary browser labels.

The planner should show all four slots for every date even when no MealEvent exists yet. A slot may still contain more than one event when the family splits.

## Ingredients

Ingredients are reusable `FoodItem` records, normally `food_kind=ingredient`.

Required product workflow:

- search/list;
- create/edit;
- attach/import nutrition evidence;
- preserve source/provenance and composition versions;
- deactivate instead of breaking referenced history.

AI or external providers may later help identify ingredients and suggest source data, but persisted calorie/nutrient calculations must remain deterministic and traceable.

## Recipes

Recipes are first-class Family assets.

Required workflow:

- list/search/filter;
- create/edit/deactivate;
- add/remove/reorder ingredients;
- quantity, unit and preparation note per ingredient;
- serving count and/or finished yield;
- preparation instructions;
- total nutrition and per-serving nutrition;
- Person ratings/preferences and Family aggregate;
- direct use from the family planner.

The existing `Recipe`, `RecipeIngredient` and versioned recipe-composition domain must be reused.

## Recipe nutrition calculation

Recipe composition is derived from authoritative ingredient composition:

```text
RecipeIngredient quantity
+ FoodCompositionSnapshot
+ safe unit conversion
-> ingredient contribution

sum contributions
-> RecipeCompositionSnapshot
-> total and per-serving nutrition
```

Do not guess unsafe mass/volume/density conversions. Missing required evidence stays visible instead of becoming zero. Recalculation creates a new recipe composition version rather than rewriting historical evidence.

## Family planner

The plan is a first-class read/write workflow, not merely an agenda.

Required actions:

- Today and Week;
- four fixed slots per day;
- add meal;
- choose Recipe or suitable FoodItem;
- choose participants;
- create Person-specific planned portions;
- edit date/time, food/recipe, participants and portions;
- replace/cancel/remove a planned meal;
- repeat/copy where useful;
- open detail/history.

A dedicated desktop planner may be denser than Family Home because weekly planning is its one primary purpose. Mobile should preserve the same four-slot model through one-day or stacked-day presentation.

## Ratings versus planning score

A person's recipe rating/preference (normally 1–5) is not the same as the recommendation engine score.

After deterministic safety filtering, planning ranking may consider:

- Person ratings/preferences;
- nutrition fit across the day;
- Family fairness;
- pantry availability;
- cooking time/practicality;
- repetition/recency;
- accepted/rejected/modified history.

The UI must not show an algorithmic planning score as though it were a user's rating.

## Pantry and shopping

The desired chain is:

```text
Planned recipes for a date range
-> aggregate ingredients
-> subtract usable pantry stock
-> shopping requirements
-> durable shopping list
```

Existing pantry sufficiency logic should be exposed only after ingredients, recipes and the planner are operational.

## Revised implementation order

1. Ingredient catalogue API + lightweight UI.
2. Recipe CRUD + ingredient editor + deterministic recipe nutrition calculation.
3. Four-slot Family planner read/write model and meal mutation APIs.
4. Planner UI with add/change/remove and recipe selection.
5. Person-specific portions integrated with planned meals.
6. Recipe ratings/preferences and recommendation-ranking integration.
7. Pantry management UI.
8. Plan-to-shopping aggregation and durable shopping-list lifecycle.
9. Resume secondary analytics/detail screens and broader health UI.

## UX principle

Continue preferring focused screens. That means more explicit workflows, not less core functionality.

A useful operational information architecture is:

```text
Plano
Receitas
Ingredientes
Despensa
Compras
Pessoas
```

Family Home remains a lightweight orientation dashboard.
