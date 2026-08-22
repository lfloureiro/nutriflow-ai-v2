# Domain implementation status

`docs/development-continuity.md` is the handover entry point. This file summarizes product/domain capability without replacing detailed ADRs and domain docs.

## Integrated baseline

Integrated through PR #33:

- Family/Person core model and Family-first application shell;
- goals, constraints, preferences/adverse reactions, schedules and health/nutrition state models;
- MealEvent -> MealParticipant -> Serving structure for shared meals and Person-specific portions;
- versioned FoodItem/Recipe composition domain;
- deterministic Serving nutrition calculation and safe unit conversion;
- hard-rule-first recommendation/ranking and persisted recommendation evidence/feedback;
- DailyNutritionState recalculation from authoritative Serving history;
- shared-family recommendation/portion logic;
- pantry stock/sufficiency and transient shopping-requirement backend logic;
- commercial availability source metadata;
- Family Home dashboard;
- Person overview;
- Family Meals `Hoje` / `Semana` read views plus existing recommendation flow.

Exact baseline:

```text
main SHA:    e0bdd8a9c8cc40f58ab67f14727ab134ac2156dc
schema head: a7c4e9f2b6d1
API tests:   110
Web tests:   19
```

## Product sequencing correction

The operational meal-planning chain now takes priority over further dashboard/detail polish:

```text
Ingredients
-> Recipes
-> Recipe nutrition
-> Family planner
-> Person portions
-> Pantry
-> Shopping
```

See `docs/vision/core-meal-planning-priorities.md`.

## Current branch: ingredient catalogue

```text
feature/core-ingredient-catalogue
base: e0bdd8a9c8cc40f58ab67f14727ab134ac2156dc
migration: none
```

Implemented on the branch:

- Family ingredient list/search API;
- create/read/update ingredient API;
- soft-delete/deactivate and reactivation;
- strict Family isolation;
- optional manual FoodCompositionSnapshot on create/update;
- each nutrition change creates a new version instead of rewriting old composition;
- common editor fields for energy, protein, carbohydrate, fat, fibre and sodium;
- web API contracts/client;
- responsive `Casa -> Ingredientes` list/search/editor;
- explicit inactive administration;
- pt-PT/en ingredient workflow copy;
- API and web tests;
- updated core meal-planning priorities and handover docs.

Expected validation on final exact head:

```text
API: 115 tests, Alembic clean, Ruff clean
Web: 24 tests, strict TypeScript/Vite build clean
```

Counts remain expectations until locally validated.

## Core assets already present for next increments

### Ingredients / food composition

`FoodItem`, `FoodCompositionSnapshot`, `FoodNutrientComponent` already provide stable identity plus versioned composition evidence.

### Recipes

`Recipe`, `RecipeIngredient`, `RecipeCompositionSnapshot` and `RecipeNutrientComponent` already exist. Missing work is primarily CRUD/editor APIs plus deterministic ingredient-to-recipe composition calculation.

### Servings

The existing Serving nutrition calculator safely scales Food or Recipe composition into planned/served/consumed Person portions while retaining provenance.

### Pantry / shopping

The backend can compare Recipe ingredient requirements with quantity-aware pantry stock and produce missing shopping requirements. The durable product workflow/UI is still missing.

## Important current gaps

1. Recipe CRUD/read UI and ingredient editor.
2. Recipe composition calculation from ingredient snapshots.
3. Restrict normal meal types to breakfast/lunch/snack/dinner at backend/domain boundary.
4. Four-slot read/write Family planner.
5. Add/edit/replace/cancel/remove meal workflows.
6. Recipe ratings/preferences distinct from algorithmic recommendation score.
7. Pantry management UI.
8. Planned-recipes -> aggregated ingredients -> pantry subtraction -> durable shopping list.
9. Authentication/Family authorization for real multi-user deployment.

## Deferred work

`feature/web-family-meal-detail` contains useful Serving-detail UI/backend work but is intentionally not being merged now. Reuse/rebase it after recipes and the planner define the main operational flow.

## Safety/correctness invariants

Preserve:

- mandatory adverse-reaction/nutrition constraints before ranking;
- missing mandatory nutrition evidence fails closed where required;
- unsafe unit conversions are rejected rather than guessed;
- no inferred density;
- exact versioned composition provenance;
- catalogue edits do not silently rewrite historical Servings;
- browser does not author authoritative nutrition totals or safety decisions;
- shared Family meals retain Person-specific portions;
- Family isolation on every Family-scoped read/write;
- missing evidence remains missing, not zero;
- warnings are failures.

## Next implementation order

1. Finish/merge ingredient catalogue after exact-head validation.
2. Recipe CRUD + ingredient editor + recipe nutrition calculation.
3. Four fixed meal types + read/write four-slot planner model.
4. Planner UI and meal mutations.
5. Person-specific planned portions.
6. Ratings/preferences and planning ranking.
7. Pantry UI.
8. Durable shopping list.
9. Resume secondary analytics and broader health UI.
