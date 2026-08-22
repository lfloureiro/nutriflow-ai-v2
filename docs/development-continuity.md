# NutriFlow AI v2 development continuity

This is the handover entry point for NutriFlow AI v2. Repository code, migrations, tests, domain/vision docs and ADRs are authoritative when conversation history differs.

## Product direction

NutriFlow AI v2 is standalone from v1.

The primary product value is practical Family meal planning supported by Person-specific nutrition:

```text
Ingredients
-> Recipes
-> Recipe nutrition
-> Family plan
-> Person-specific portions
-> Pantry
-> Shopping
-> history / feedback
```

Family Home remains a lightweight orientation dashboard. Detailed health/analytics work is secondary until the operational meal-planning chain is usable.

## Core invariants

- Person remains the primary nutrition entity inside Family context;
- one shared MealEvent can have multiple MealParticipants;
- each participant has Person-specific Servings;
- normal meal planning uses exactly breakfast, lunch, snack and dinner;
- Food/Recipe composition is versioned and historical provenance is preserved;
- hard safety/mandatory nutrition rules run before ranking/ML;
- missing evidence is unknown, never silently zero;
- browser code presents server-authoritative nutrition and does not reproduce nutrition/safety calculations;
- catalogue cleanup does not destructively break historical meal evidence;
- demo data is explicit, synthetic and never auto-seeded.

## Mandatory delivery workflow

Authoritative decision: `docs/decisions/ADR-007-development-workflow-and-ci.md`.

The user has requested larger integrations for speed. Delivery therefore uses larger coherent functional branches, while retaining the validation/merge safeguards:

1. resolve exact baseline;
2. build one coherent end-to-end block with code/tests/docs;
3. run all relevant local gates on the exact final head;
4. warnings are failures;
5. PR only after explicit local green confirmation;
6. CI must pass on exact PR head;
7. confirm mergeability/head unchanged;
8. guarded squash merge;
9. verify resulting `main`;
10. start the next large block.

## Last integrated checkpoint

```text
main SHA:    e0bdd8a9c8cc40f58ab67f14727ab134ac2156dc
schema head: a7c4e9f2b6d1
API tests:   110
Web tests:   19
```

PR #33 is the last integrated PR on that baseline.

## Current large integration branch

```text
feature/core-meal-planning-foundation
```

The branch was created from the completed ingredient-catalogue head:

```text
c0a47011ab5acd1f79acd71d9d3e4f8e164cc11e
```

That ancestor itself descends directly from integrated `main` `e0bdd8a9...`, so the eventual PR contains the complete core block from `main`:

### 1. Ingredients

- Family ingredient list/search;
- create/edit identity and nutrition evidence;
- versioned FoodCompositionSnapshot on nutrition changes;
- deactivate/reactivate rather than destructive delete;
- lightweight `Casa -> Ingredientes` UI.

### 2. Recipes

- Family Recipe CRUD/search/deactivate/reactivate;
- ordered RecipeIngredient editor;
- quantities, units and preparation notes;
- serving count and finished yield;
- deterministic `recipe-nutrition-v1` calculation;
- new RecipeCompositionSnapshot on nutrition-relevant Recipe changes;
- total and per-serving energy/nutrients;
- explicit issues for missing/unsafe nutrition evidence;
- no client-side calorie calculation.

### 3. Four fixed meal types

Shared server contract:

```text
breakfast
lunch
snack
dinner
```

The new planner and existing recommendation request APIs reject arbitrary meal-type strings.

### 4. Editable Family meal plan

New API:

```text
GET    /api/families/{family_id}/meal-plan
POST   /api/families/{family_id}/meal-plan
PATCH  /api/families/{family_id}/meal-plan/{meal_event_id}
DELETE /api/families/{family_id}/meal-plan/{meal_event_id}
```

- Family-local Today/Week ranges;
- exactly four visible slots every day, including empty slots;
- create a planned Recipe meal;
- select Family participants;
- optional Person-specific planned quantities;
- default portion from Recipe yield/serving-count evidence;
- Serving nutrition calculated server-side from current RecipeCompositionSnapshot;
- edit date/time/type/Recipe/participants/portions while status is planned;
- remove by cancellation rather than destructive deletion;
- prepared/served/completed MealEvents are locked against planning edits.

### 5. Web workflow

`Casa` now has focused subflows:

```text
Receitas | Ingredientes
```

`Refeições` now functions as the meal planner:

```text
Hoje | Semana | Recomendar
```

Today/Week expose the four slots and add/edit/remove operations. The old recommendation workflow remains reachable but is secondary.

## Expected validation baseline

Current expected counts before local execution:

```text
API: 120 pytest tests
Web: 27 Vitest tests
```

Counts remain expectations until the exact final branch head passes local validation. There is currently no new database migration in this branch; the four-type business rule is enforced at server write/API boundaries.

Validation:

```powershell
cd D:\Python\nutriflow-ai-v2
python -m alembic check

cd apps\api
python -m ruff check .
python -m pytest -q

cd ..\web
npm install --no-package-lock --ignore-scripts
npm run test
npm run build
```

Do not open the PR until the exact final branch head is explicitly confirmed green locally.

## Deferred work preserved

`feature/web-family-meal-detail` remains unmerged. Its Person-specific meal-detail presentation can be reused later, but the current planner now already materializes Person-specific Servings where they belong.

## Demo

Fixed Family ID:

```text
11111111-1111-4111-8111-111111111111
```

The existing demo still seeds the prior synthetic Family/Person/meal/recommendation dataset. It does not yet pre-seed the new ingredient/Recipe catalogue, so the core smoke test starts by creating ingredients and a Recipe through the normal UI. This deliberately validates the new creation workflows themselves.

## Next large integration after merge

The next block is:

```text
Pantry management
+ planned Recipe ingredient aggregation
+ subtract available stock
+ Shopping requirements
+ durable ShoppingList lifecycle/UI
```

Recipe ratings/preferences and recommendation-score integration can follow that operational chain, before secondary analytics/dashboard expansion.

## Known broader limitations

- Family UUID remains development context, not production authorization;
- production authentication/Family authorization is not implemented;
- persistent DB-level MealEvent `meal_type` check constraint is not yet added; all current user-facing write APIs use the fixed server contract;
- pantry sufficiency logic exists but no normal pantry UI yet;
- shopping requirements are still transient backend logic rather than a durable ShoppingList product flow;
- recipe preference/rating UX is not yet implemented;
- npm lockfile / `npm ci` production hardening remains pending.

## Resume procedure

1. read this file, ADR-007 and the core meal-planning priority docs;
2. inspect exact `main`, active branch and compare state;
3. confirm exact final branch head and local gate result;
4. never PR/merge an unvalidated head;
5. after merge verify exact new `main` before starting Pantry + Shopping.
