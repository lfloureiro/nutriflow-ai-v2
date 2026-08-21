# NutriFlow AI v2 development continuity

This document is the handover entry point for resuming NutriFlow AI v2 development in a later session. It records the current repository checkpoint, the mandatory development workflow and where the authoritative design information lives.

It is intentionally a continuity map rather than a second copy of all domain documentation. When details differ, the relevant domain document, ADR, migration and code on the current branch are authoritative.

## Product and architecture baseline

NutriFlow AI v2 is a standalone implementation. It must not depend on a legacy repository, legacy schema or compatibility layer.

Core direction:

- Person-centric nutrition model;
- Person belongs to a Family;
- shared Family meals use one MealEvent with person-specific MealParticipant and Serving records;
- safety and mandatory nutrition rules are deterministic and cannot be bypassed by learned ranking;
- health-provider data is normalized with provenance and remains in a health/wellness boundary rather than autonomous diagnosis/treatment;
- historical source records remain authoritative while DailyHealthState and DailyNutritionState are derived/recalculable snapshots;
- versioned food/recipe composition is used for reproducible Serving nutrition and recommendation decisions;
- recommendation history and feedback remain audit evidence rather than authoritative meal-plan state;
- multilingual, responsive, light/dark/system-capable web/mobile product direction remains part of the intended platform.

The current API namespace is `/api/...`; there is no `/api/v1` compatibility requirement.

## Mandatory development workflow

The authoritative workflow is ADR-007: `docs/decisions/ADR-007-development-workflow-and-ci.md`.

In abbreviated form:

1. start from the exact current `main` SHA;
2. create one focused feature branch;
3. implement code, migration, tests and relevant documentation together;
4. test locally against PostgreSQL;
5. require Alembic metadata, Ruff and the complete pytest suite to pass with zero warnings;
6. open a PR only after local validation is explicitly green;
7. verify GitHub Actions on the exact PR head SHA;
8. confirm the PR is mergeable and its head has not changed;
9. squash-merge guarded by the exact tested head SHA;
10. verify the merged PR and resulting exact `main` SHA;
11. only then create the next feature branch.

Do not commit directly to `main`. Do not merge an untested branch. Do not treat CI for an earlier SHA as validation of a later SHA. Documentation is part of the definition of done.

## Local environment and validation

Current backend baseline:

- Python >= 3.13;
- FastAPI;
- SQLAlchemy 2.x;
- Alembic;
- PostgreSQL;
- psycopg 3.x;
- pytest with warnings treated as errors;
- Ruff target `py313`, line length 100.

Typical schema-changing branch validation from the repository root:

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic check

cd apps\api
python -m ruff check .
python -m pytest -q
```

For a branch without schema changes, `alembic upgrade head/current` are optional but `alembic check`, Ruff and the complete pytest suite remain required.

The local development database configuration and migration bootstrap are defined in the repository configuration and Alembic environment. CI independently applies the complete migration chain to an empty PostgreSQL database.

## Current repository checkpoint

Last fully integrated feature before the current branch:

- PR #18: persisted practical meal availability;
- resulting `main` SHA: `d2fbda5e2a3770a35fcb500bb163e888cdf93bfd`;
- schema head on that `main`: `e5a2c7d9f4b1`;
- validated test baseline after PR #18: 58 tests.

Current feature branch:

- branch: `feature/pantry-stock-shopping-requirements`;
- merge base: `d2fbda5e2a3770a35fcb500bb163e888cdf93bfd`;
- current branch introduces migration `f6b3d8e1a5c2`;
- expected complete test baseline: 64 tests;
- PR has not yet been opened at this checkpoint;
- branch must receive explicit local green confirmation before PR creation.

The current branch implements:

- Family-scoped `PantryStockLot` operational stock records;
- quantity and unit per stock lot;
- optional expiry and explicit availability state;
- safe aggregation across compatible mass or volume units;
- expired/unavailable stock exclusion;
- deterministic Recipe ingredient sufficiency evaluation;
- duplicate RecipeIngredient aggregation before stock comparison;
- exact missing quantities represented as shopping requirements;
- candidate-level pantry availability profiles for FoodItem and Recipe recommendation candidates;
- Recipe candidate scaling from requested candidate quantity to recipe yield;
- fail-closed behaviour for unsafe mass/volume conversion and cross-Family catalogue references;
- migration, tests, domain documentation and ADR-024.

Current branch authoritative documents:

- `docs/domain/pantry-stock-shopping-requirements.md`;
- `docs/decisions/ADR-024-pantry-stock-is-family-scoped-operational-state.md`;
- `docs/domain/implementation-status.md`.

## Current migration chain

The current branch migration head is:

```text
f6b3d8e1a5c2
```

It follows:

```text
e5a2c7d9f4b1  persisted meal candidate availability
d4f8a1b2c6e9  MealEvent idempotency
c3e7f9a1b5d2  recommendation run/option/feedback
```

Earlier migration history remains authoritative in `database/migrations/versions/` and is summarized in `docs/domain/implementation-status.md`.

Never invent or reorder a migration revision when resuming work. Inspect the current branch and `alembic current/heads` before adding another migration.

## Implemented capability map

Use `docs/domain/implementation-status.md` as the compact current-status document. Detailed domain semantics are split across documents including:

- `docs/domain/core-domain-model.md`;
- `docs/domain/schedule-model.md`;
- `docs/domain/nutrition-target-model.md`;
- `docs/domain/health-connection-model.md`;
- `docs/domain/health-measurement-model.md`;
- `docs/domain/daily-state-model.md`;
- `docs/domain/daily-nutrition-recalculation.md`;
- `docs/domain/meal-model.md`;
- `docs/domain/food-catalog-model.md`;
- `docs/domain/serving-nutrition-calculation.md`;
- `docs/domain/adaptive-meal-recommendation.md`;
- `docs/domain/recommendation-feedback-model.md`;
- `docs/domain/recommendation-to-meal-plan.md`;
- `docs/domain/recommendation-practical-context.md`;
- `docs/domain/shared-family-meal-optimization.md`;
- `docs/domain/shared-family-meal-materialization.md`;
- `docs/domain/meal-replacement-idempotency.md`;
- `docs/domain/persisted-practical-availability.md`;
- `docs/domain/pantry-stock-shopping-requirements.md`.

Durable architecture/design choices are recorded under `docs/decisions/`. ADR-007 governs workflow; later ADRs cover domain decisions for the corresponding capability increments.

## Important safety and correctness invariants

These invariants must remain true across future increments:

- mandatory adverse reactions and mandatory constraints are evaluated before ranking;
- learned/ML ranking may reorder eligible options but may never make an ineligible option eligible;
- unsupported mandatory semantics and unsafe required unit conversions fail closed;
- Serving nutrition uses explicit versioned composition provenance;
- no inferred density is used for mass/volume conversion;
- historical recommendations and feedback remain append-only evidence;
- materialized meal plans use normal MealEvent/MealParticipant/Serving records;
- DailyNutritionState derives from authoritative meal/Serving history and is recalculable;
- Family-specific catalogue and operational records cannot leak across Families;
- shared meals retain person-specific portions and person-specific safety evaluation;
- retries and plan replacements must preserve idempotency and immutable replacement history;
- warnings are treated as test failures rather than suppressed casually.

One known area for a future dedicated safety-hardening increment is the behaviour of mandatory nutrient maxima when a candidate has no value for the constrained nutrient. Do not silently change this as an unrelated side effect; review and document the fail-closed policy explicitly when that increment is scheduled.

## Next planned increments

After the current pantry-stock branch is locally validated, PR-tested and merged, the planned sequence is synchronized with `docs/domain/implementation-status.md`:

1. add restaurant/delivery commercial context such as price, opening hours and provider synchronization;
2. expose coherent API and UI vertical slices over the completed planning flow;
3. persist shopping-list lifecycle when API/UI workflows require durable shopping state;
4. add background/event-driven DailyNutritionState refresh and explicit target-selection policy;
5. extend recurrence/calendar override support;
6. persist family-level recommendation audit history where needed;
7. harden transaction-level idempotency races at the write API boundary;
8. introduce learned ranking from feedback only after deterministic safety, practical and nutrition layers remain authoritative.

The exact next increment may be reordered deliberately, but any change to this sequence must be reflected in both `docs/domain/implementation-status.md` and this continuity document.

## How to resume safely in a later session

When returning to the project:

1. read this file;
2. read ADR-007;
3. inspect `docs/domain/implementation-status.md`;
4. inspect `git status`, current branch, `git log -1`, `git branch -vv` and remote state;
5. compare the active feature branch to `main` before assuming the checkpoint above is still current;
6. inspect the current Alembic head rather than relying only on the revision written here;
7. run or request the local validation gates before opening a PR;
8. after a merge, update this document with the new `main` SHA, migration/test baseline, active branch and next safe step.

Repository state, tests and documentation are the source of truth. Conversation history may help with context, but it is never required to reconstruct the approved workflow or current architecture.
