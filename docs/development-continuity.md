# NutriFlow AI v2 development continuity

This document is the handover entry point for resuming NutriFlow AI v2 development in a later session. It records the current repository checkpoint, mandatory workflow, safety invariants and next planned steps so development can continue from the repository without relying on conversation history.

When details differ, repository state, code, migrations, tests, the relevant domain document and ADR are authoritative.

## Product and architecture baseline

NutriFlow AI v2 is standalone. Do not introduce legacy repository/schema dependencies or compatibility layers unless a future explicit decision changes that direction.

Core architecture:

- Person belongs to Family;
- shared meals use one MealEvent with person-specific MealParticipant and Serving rows;
- safety and mandatory nutrition rules are deterministic and cannot be bypassed by learned ranking;
- food/recipe composition is versioned for reproducible Serving and recommendation calculations;
- DailyHealthState/DailyNutritionState are derived and recalculable;
- recommendation history/feedback are audit evidence rather than authoritative meal-plan state;
- practical, pantry and commercial source data are operational state separate from nutrition composition;
- API namespace is `/api/...`, not `/api/v1`;
- multilingual, responsive web/mobile and light/dark/system support remain product requirements.

## Mandatory workflow

Authoritative decision: `docs/decisions/ADR-007-development-workflow-and-ci.md`.

Use this sequence for every non-trivial increment:

1. verify the exact current `main` SHA;
2. create one focused branch from that SHA;
3. implement code, migration, tests and relevant documentation together;
4. run local PostgreSQL/migration validation;
5. require `alembic check`, Ruff and the complete pytest suite to pass with zero warnings;
6. open a PR only after explicit local green confirmation;
7. verify GitHub Actions on the exact PR head SHA;
8. confirm PR mergeability and unchanged head SHA;
9. squash-merge guarded by the tested head SHA;
10. verify the merged PR and resulting exact `main` SHA;
11. only then create the next branch;
12. refresh this continuity checkpoint on that next branch.

Never commit feature work directly to `main`. Never merge an untested head. CI for an earlier SHA does not validate a later SHA. Documentation is part of the Definition of Done.

## Local validation commands

For a schema-changing branch, from repository root:

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic check

cd apps\api
python -m ruff check .
python -m pytest -q
```

For a branch without schema changes, `alembic upgrade head/current` are optional, but `alembic check`, Ruff and the complete pytest suite remain required.

Current backend baseline:

- Python >= 3.13;
- FastAPI;
- SQLAlchemy 2.x;
- Alembic;
- PostgreSQL;
- psycopg 3.x;
- pytest warnings treated as errors;
- Ruff target `py313`, line length 100.

## Last integrated checkpoint

PR #21 integrated fail-closed handling for missing candidate nutrient data under mandatory nutrient maxima.

Exact integrated baseline:

```text
main SHA:        09ca2f235d770b87f128dc8448fe9768b2801ad2
schema head:     a7c4e9f2b6d1
test baseline:   72 tests
```

PR #21 was locally validated, passed CI on the exact tested head and was squash-merged.

Integrated safety behaviour now includes:

- missing candidate nutrient data cannot satisfy an active mandatory nutrient maximum;
- missing data excludes only that candidate as `mandatory_nutrient_data_missing:<nutrient_key>`;
- an explicit zero remains valid measured data;
- unsupported mandatory semantics and unsafe mandatory conversions still fail closed.

Detailed semantics: `docs/domain/adaptive-meal-recommendation.md`, ADR-026.

## Current feature branch

Current branch:

```text
feature/planning-api-vertical-slice
```

Merge base:

```text
09ca2f235d770b87f128dc8448fe9768b2801ad2
```

Schema head remains:

```text
a7c4e9f2b6d1
```

This branch has no database migration.

Expected complete test baseline after its six API integration tests:

```text
78 tests
```

No PR should be opened until this branch receives explicit local green confirmation for Alembic metadata, Ruff and all tests.

### Current branch scope

The branch exposes the first persisted person-scoped recommendation API:

```text
POST /api/persons/{person_id}/meal-recommendations
```

The endpoint:

- requires one explicit persisted DailyNutritionState ID;
- requires `planning_date` to match that state's date;
- requires explicit FoodCompositionSnapshot/RecipeCompositionSnapshot IDs;
- requires positive candidate quantity and explicit unit;
- reloads all source evidence from persistence;
- validates Person ownership and Family isolation;
- rejects inactive catalogue candidates;
- rejects duplicate catalogue candidate keys;
- fails explicitly on unsafe candidate quantity scaling;
- reuses the existing deterministic `recommend_meals()` engine rather than duplicating safety/ranking logic;
- persists one MealRecommendationRun and every eligible/excluded MealRecommendationOption;
- returns persisted run/option IDs, ranks, scores, explanations, exclusions and calculated nutrition snapshots;
- records API entrypoint and explicit composition IDs in recommendation context.

Authoritative current-branch docs:

- `docs/domain/planning-api-vertical-slice.md`;
- `docs/decisions/ADR-027-recommendation-api-requires-explicit-state-and-composition-snapshots.md`;
- `docs/domain/implementation-status.md`.

## Current migration tail

```text
a7c4e9f2b6d1  commercial source opening windows and offers
f6b3d8e1a5c2  quantity-aware Family pantry stock lots
e5a2c7d9f4b1  Family-scoped meal candidate availability
d4f8a1b2c6e9  MealEvent Family-scoped idempotency
c3e7f9a1b5d2  recommendation run/option/feedback
```

Earlier revisions remain authoritative in `database/migrations/versions/` and are summarized in `docs/domain/implementation-status.md`.

Never guess the next revision. Inspect the migration directory and actual Alembic heads/current state before adding another migration.

## Safety and correctness invariants

Preserve these across all future work:

- mandatory adverse reactions and mandatory constraints run before ranking;
- learned/ML ranking can reorder eligible candidates only;
- missing candidate nutrient data cannot be interpreted as zero for a mandatory maximum;
- unsupported mandatory semantics fail explicitly;
- unsafe required unit conversions fail closed;
- no inferred density for mass/volume conversion;
- Serving nutrition keeps explicit versioned composition provenance;
- recommendation API inputs reference explicit persisted state/composition evidence rather than client-authored nutrition totals;
- historical recommendation/feedback evidence remains append-only;
- materialized plans use normal MealEvent/MealParticipant/Serving records;
- DailyNutritionState derives from authoritative meal history;
- Family-scoped catalogue/operational data cannot leak across Families;
- shared meals retain person-specific portions and safety evaluation;
- retries and plan replacement preserve idempotency and immutable history;
- commercial availability/price cannot make a safety-ineligible candidate eligible;
- warnings are treated as failures rather than casually suppressed.

A separate future decision may be needed if a mandatory nutrient maximum applies but historical DailyNutritionState does not contain enough consumed/planned data for that nutrient. Do not silently treat missing historical state as complete evidence.

## Implemented capability map

Use `docs/domain/implementation-status.md` as the compact status map. Detailed domain documents include:

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
- `docs/domain/pantry-stock-shopping-requirements.md`;
- `docs/domain/restaurant-delivery-commercial-context.md`;
- `docs/domain/planning-api-vertical-slice.md`.

Durable decisions are under `docs/decisions/`; ADR-007 governs workflow.

## Next planned increments

After the current recommendation API branch is locally green, PR-tested and merged:

1. expose recommendation feedback and accepted-option meal materialization through focused API endpoints;
2. expose practical schedule/source/pantry/commercial context through API orchestration without weakening hard-rule semantics;
3. begin the first responsive web UI vertical slice over the stable recommendation API;
4. persist shopping-list lifecycle when API/UI workflows require durable shopping state;
5. add background/event-driven DailyNutritionState refresh and explicit target-selection policy;
6. extend recurrence/calendar override support;
7. persist family-level recommendation audit history;
8. harden transaction-level idempotency races at the write API boundary;
9. add provider connectors/live freshness policy, basket/order lifecycle and commercial optimization;
10. introduce learned ranking only after deterministic safety/practical/nutrition layers remain authoritative.

Any deliberate roadmap reordering must update both this file and `docs/domain/implementation-status.md`.

## Resume procedure for a later session

1. read this file;
2. read ADR-007;
3. read `docs/domain/implementation-status.md`;
4. inspect `git status`, current branch, `git log -1`, `git branch -vv` and remote state;
5. compare the active feature branch with `main`;
6. inspect actual Alembic heads/current state;
7. verify whether the branch already received local green validation;
8. do not open or merge a PR unless the exact active head satisfies the workflow;
9. after merge, verify new `main`, create the next focused branch, then update this file.

Repository state, tests and documentation are the source of truth. Conversation history is optional context only.
