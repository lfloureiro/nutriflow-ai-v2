# NutriFlow AI v2 — Core meal-planning priorities

## Purpose

The core user value of NutriFlow is practical family meal planning. Health dashboards, Person drill-downs and recommendation explanations support that goal, but must not displace the operational workflows required to plan what the family will eat.

The product should make the following chain easy and explicit:

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

## Non-negotiable meal structure

The normal family planner uses exactly four meal types:

1. `breakfast` — Pequeno-almoço
2. `lunch` — Almoço
3. `snack` — Lanche
4. `dinner` — Jantar

These are domain values, not arbitrary browser labels. The backend must validate them.

A planning date exposes all four slots even when no MealEvent exists yet. A slot may contain zero or more MealEvents so split-family situations remain possible, but the normal UX should optimise for one shared family event where practical.

## Family planner

The meal plan is a first-class workflow, not merely a read-only agenda.

Required actions:

- view today and week;
- see all four meal slots per day, including empty slots;
- add a meal to a slot;
- select a Recipe or appropriate FoodItem;
- choose participants;
- create Person-specific planned portions;
- edit date/time, recipe/food, participants and portions;
- replace a planned meal;
- remove/cancel a planned meal;
- copy/repeat a meal where useful;
- open meal detail/history.

Desktop may use a compact week planning grid because this is a dedicated planning screen. Mobile should use one day at a time or vertically stacked day sections with the same four fixed slots.

## Ingredient catalogue

Ingredients are reusable `FoodItem` records, normally `food_kind=ingredient`.

Required workflow:

- search existing ingredients;
- create a Family ingredient when it does not exist;
- edit descriptive data;
- attach or import nutrition composition;
- keep composition source/provenance;
- deactivate rather than destructively delete referenced catalogue data.

Nutrition assistance may use AI/provider matching to identify an ingredient or suggest source data, but persisted calorie/nutrient calculation must remain deterministic and traceable to composition evidence.

## Recipe management

Recipes are a first-class Family asset.

Required workflow:

- list/search/filter recipes;
- create recipe;
- edit recipe;
- deactivate/delete when safe;
- add/remove/reorder ingredients;
- specify ingredient quantity/unit and preparation notes;
- specify serving count and/or finished yield;
- store preparation instructions;
- show total recipe nutrition;
- show nutrition per serving and scalable quantity;
- show Person/family preference information;
- use the recipe directly from the family planner.

The existing `Recipe` / `RecipeIngredient` / `RecipeCompositionSnapshot` domain model should be reused rather than replaced.

## Recipe nutrition calculation

NutriFlow must calculate recipe nutrition from its ingredients.

Conceptually:

```text
RecipeIngredient quantity
+ authoritative FoodCompositionSnapshot
+ safe unit conversion
-> ingredient nutrition contribution

sum ingredient contributions
-> RecipeCompositionSnapshot
-> energy and nutrient totals
-> per-serving / per-yield values
```

Rules:

- use an explicit composition snapshot for every contributing ingredient;
- persist calculation provenance/version;
- do not guess unsafe mass/volume conversions or density;
- missing required composition evidence must be visible rather than silently treated as zero;
- changing ingredient composition creates/recalculates a new recipe composition snapshot rather than rewriting history.

The existing Serving nutrition calculator can then scale a RecipeCompositionSnapshot into each Person-specific Serving.

## Recipe ratings and planning score

User preference and algorithmic recommendation score are different concepts and must remain separate.

The product needs a clear recipe rating/preference workflow per Person, normally 1–5, with a useful Family aggregate for display.

A planning/recommendation score may combine only after deterministic safety filtering:

- Person ratings/preferences;
- nutrition fit for each participant/day;
- family fairness;
- pantry availability;
- cooking practicality/time;
- repetition/recency;
- observed accept/reject/modify history.

The UI must not present an algorithmic score as though it were a user's star rating.

## Pantry and shopping

The existing pantry sufficiency logic is strategically important and should be exposed after recipes/planner are operational.

Required chain:

```text
Planned recipes for date range
-> aggregate ingredient requirements
-> subtract usable pantry stock
-> shopping requirements
-> durable shopping list
```

The shopping list should later support manual items, checked/purchased state and quantity adjustments; it must not be only a transient recommendation result.

## Current backend assets to preserve

Already useful foundations include:

- `FoodItem` and versioned `FoodCompositionSnapshot`;
- `Recipe`, `RecipeIngredient`, `RecipeCompositionSnapshot`;
- `MealEvent`, `MealParticipant`, `Serving`;
- deterministic Serving nutrition scaling;
- shared-family recommendation/portion logic;
- pantry stock and recipe ingredient sufficiency logic;
- DailyNutritionState and recommendation safety/ranking infrastructure.

The correction is therefore primarily product sequencing and missing CRUD/calculation APIs, not a rewrite of the backend model.

## Current gaps to close before further dashboard/detail polish

1. enforce the four meal types at the domain/API boundary;
2. ingredient catalogue CRUD/read APIs and UI;
3. recipe CRUD/read APIs and UI;
4. deterministic recipe-composition calculation from ingredients;
5. family meal-plan mutation APIs: add/edit/replace/cancel/delete semantics;
6. planner UI with four fixed slots per day;
7. recipe rating/preference workflow distinct from recommendation score;
8. pantry UI and plan-to-shopping aggregation;
9. durable shopping-list lifecycle.

## Revised implementation order

1. Core ingredient catalogue API + lightweight UI.
2. Recipe CRUD, ingredient editor and recipe nutrition calculation.
3. Four-slot Family planner read/write model and meal mutation APIs.
4. Planner UI: Today/Week with add/change/remove and recipe selection.
5. Person-specific portions integrated into planned meals.
6. Recipe ratings/preferences and recommendation ranking integration.
7. Pantry management UI.
8. Shopping requirements from planned recipes, then durable shopping list.
9. Resume secondary analytics/detail screens and broader health UI.

## UX principle

NutriFlow should still prefer light focused screens. That means more explicit workflows, not less functionality:

```text
Plano
Receitas
Ingredientes
Despensa
Compras
Pessoas
```

Each can be a focused screen. Family Home remains an orientation dashboard, while the dedicated Planner is allowed to be denser because planning the week is its single purpose.
