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

PR #20 integrated restaurant/delivery/store commercial planning context.

Exact integrated baseline:

```text
main SHA:        4f7c56a1c609665fb6c06168df96fdc3e977bf26
schema head:     a7c4e9f2b6d1
test baseline:   71 tests
```

PR #20 was locally validated, passed CI on the exact tested head and was squash-merged.

Integrated commercial capability includes:

- MealSourceOpeningWindow linked to MealCandidateAvailability;
- weekly local opening windows with explicit timezone;
- same-day, overnight and full-day semantics;
- absent hours treated as unknown rather than closed;
- MealCommercialOffer with Family/provider identity;
- item price/currency plus optional delivery fee and minimum order;
- offer validity and provider observation time;
- deterministic commercial practical-context evaluation;
- no FX inference and no commercial override of nutrition/safety eligibility.

Detailed semantics: `docs/domain/restaurant-delivery-commercial-context.md`, ADR-025.

## Current feature branch

Current branch:

```text
fix/fail-closed-missing-mandatory-nutrient
```

Merge base:

```text
4f7c56a1c609665fb6c06168df96fdc3e977bf26
```

Schema head remains:

```text
a7c4e9f2b6d1
```

This branch has no database migration.

Expected complete test baseline after its focused regression test:

```text
72 tests
```

No PR should be opened until this branch receives explicit local green confirmation for Alembic metadata, Ruff and all tests.

### Current branch scope

The branch hardens mandatory nutrient maximum semantics:

- a candidate must contain an explicit value for every nutrient governed by an active mandatory maximum;
- missing candidate nutrient data is not treated as zero;
- missing data excludes that candidate as `mandatory_nutrient_data_missing:<nutrient_key>`;
- an explicit measured zero remains valid data;
- the exclusion is candidate-scoped, allowing other candidates with sufficient evidence to continue;
- unsupported mandatory rules and unsafe unit conversion continue to fail closed;
- one regression test proves missing data and known zero are distinct;
- no schema change.

Authoritative current-branch docs:

- `docs/domain/adaptive-meal-recommendation.md`;
- `docs/decisions/ADR-026-mandatory-nutrient-maxima-require-candidate-data.md`;
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
- `docs/domain/restaurant-delivery-commercial-context.md`.

Durable decisions are under `docs/decisions/`; ADR-007 governs workflow.

## Next planned increments

After the current safety branch is locally green, PR-tested and merged:

1. API and UI vertical slices over the deterministic planning flow;
2. persisted shopping-list lifecycle when API/UI workflows need durable shopping state;
3. background/event-driven DailyNutritionState refresh and explicit target-selection policy;
4. fuller recurrence/calendar override support;
5. persisted family-level recommendation audit history;
6. transaction-level idempotency-race handling at the write API boundary;
7. provider connectors/live freshness policy, basket/order lifecycle and commercial optimization;
8. explicit historical-nutrient-state safety policy if needed;
9. learned ranking from feedback only after deterministic safety/practical/nutrition layers remain authoritative.

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
