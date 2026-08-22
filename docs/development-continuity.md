# NutriFlow AI v2 development continuity

This is the handover entry point for NutriFlow AI v2. Repository code, migrations, tests, domain/vision docs and ADRs are authoritative when conversation history differs.

## Product direction

NutriFlow AI v2 is standalone from v1.

The primary product value is practical Family meal planning supported by Person-specific nutrition. The operational chain now has explicit priority:

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

See `docs/vision/core-meal-planning-priorities.md`.

Family Home remains a lightweight orientation dashboard. Detailed health/analytics work is secondary until the core meal-planning workflows above are usable.

## Core invariants

- Person remains the primary nutrition entity and belongs to Family context;
- one shared MealEvent can have multiple MealParticipants;
- each participant can have Person-specific Servings;
- Food/Recipe composition is versioned and historical provenance is preserved;
- hard safety/mandatory nutrition rules run before ranking/ML;
- missing evidence is unknown, never silently zero;
- the browser presents server-authoritative state and does not reimplement nutrition/safety rules;
- catalogue cleanup must not silently rewrite or break historical meal evidence;
- demo data is explicit, synthetic and never auto-seeded.

## Mandatory workflow

Authoritative decision: `docs/decisions/ADR-007-development-workflow-and-ci.md`.

For each non-trivial increment:

1. resolve exact current `main` SHA;
2. create one focused branch from that exact SHA;
3. implement code, migration when needed, tests and docs together;
4. run all relevant local gates;
5. warnings are failures;
6. open PR only after explicit local green confirmation;
7. verify every relevant GitHub Actions workflow on the exact PR head SHA;
8. confirm mergeability and unchanged head;
9. squash-merge guarded by expected head SHA;
10. verify merged PR and exact resulting `main` SHA;
11. only then start the next implementation branch.

## Validation commands

API:

```powershell
cd D:\Python\nutriflow-ai-v2
python -m alembic check

cd apps\api
python -m ruff check .
python -m pytest -q
```

Schema-changing branches additionally run upgrade/current checks.

Web:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\web
npm install --no-package-lock --ignore-scripts
npm run test
npm run build
```

Warnings are failures.

## Last integrated checkpoint

PR #33 added Family Meals `Hoje` and `Semana` read views and was locally validated, CI-green on its exact head and guarded squash-merged.

```text
main SHA:    e0bdd8a9c8cc40f58ab67f14727ab134ac2156dc
schema head: a7c4e9f2b6d1
API tests:   110
Web tests:   19
```

## Current focused branch

```text
feature/core-ingredient-catalogue
```

Exact merge base:

```text
e0bdd8a9c8cc40f58ab67f14727ab134ac2156dc
```

No database migration is expected because `FoodItem`, `FoodCompositionSnapshot` and `FoodNutrientComponent` already exist.

### Scope

- Family ingredient list/search;
- create/edit ingredient identity;
- optional manual nutrition evidence;
- common editor fields for energy, protein, carbohydrate, fat, fibre and sodium;
- each nutrition edit creates a new versioned FoodCompositionSnapshot;
- deactivate instead of hard-delete;
- include inactive items for administration and allow reactivation;
- strict Family isolation;
- lightweight responsive web list/editor under `Casa`;
- pt-PT/en UI copy;
- no Recipe CRUD or recipe-calculation logic yet.

Expected local baseline after implementation:

```text
API: Alembic clean, Ruff clean, 115 pytest tests
Web: 24 Vitest tests, strict TypeScript/Vite build clean
```

These counts are expectations only until the exact final branch head is locally validated.

Relevant docs:

- `docs/vision/core-meal-planning-priorities.md`;
- `docs/domain/ingredient-catalogue-workflow.md`;
- `docs/domain/food-catalog-model.md`;
- `docs/domain/core-domain-model.md`.

Do not open a PR until the exact final branch head receives explicit local green confirmation.

## Deferred branch

The unmerged branch:

```text
feature/web-family-meal-detail
```

contains useful Family-meal detail / Person Serving presentation work. It is deliberately deferred, not discarded. Do not merge it now. Reuse/rebase relevant parts after Recipe CRUD and the read/write Family planner establish the correct operational flow.

## Demo execution

```powershell
cd D:\Python\nutriflow-ai-v2\apps\api
python -m app.demo_seed
```

Fixed demo Family ID:

```text
11111111-1111-4111-8111-111111111111
```

The ingredient catalogue does not auto-seed ingredients in this increment. Its empty state and manual creation workflow should be smoke-tested directly.

## Current implementation sequence

1. Ingredient catalogue API + lightweight UI — current branch.
2. Recipe CRUD + ingredient editor + deterministic recipe nutrition calculation.
3. Enforce the four normal meal types at backend/domain boundary:
   - breakfast / Pequeno-almoço;
   - lunch / Almoço;
   - snack / Lanche;
   - dinner / Jantar.
4. Four-slot Family planner read/write model and add/edit/replace/cancel/remove APIs.
5. Planner UI for Today/Week with recipe selection.
6. Person-specific portions integrated into planned meals.
7. Recipe ratings/preferences separate from recommendation score.
8. Pantry management UI.
9. Planned-recipe ingredient aggregation -> pantry subtraction -> durable shopping list.
10. Resume secondary Person analytics/health detail.

## Known broader limitations

- Family UUID is still development context, not authorization;
- no production authentication/Family authorization yet;
- Recipe models exist but do not yet have normal CRUD APIs/UI;
- recipe composition is modeled but ingredient-to-recipe calculation is not yet exposed as a product workflow;
- current MealEvent `meal_type` is still a free string and must be constrained in the planner increment;
- current Family meals screen is read-oriented rather than a four-slot read/write planner;
- pantry sufficiency logic exists in backend but has no normal UI;
- durable shopping-list lifecycle is not yet exposed;
- npm lockfile / `npm ci` production hardening remains pending.

## Resume procedure

1. read this file, ADR-007 and `docs/vision/core-meal-planning-priorities.md`;
2. inspect exact `main`, active branch and compare state;
3. inspect migration heads/current state;
4. confirm whether the exact current branch head received local green validation;
5. never PR/merge an unvalidated head;
6. after merge verify the exact new `main` SHA before starting Recipe work.
