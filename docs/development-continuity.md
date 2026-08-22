# NutriFlow AI v2 development continuity

This document is the handover entry point for resuming NutriFlow AI v2 development. Repository state, migrations, tests, domain/UX docs and ADRs are authoritative when they differ from conversation history.

## Product and architecture baseline

NutriFlow AI v2 is standalone. Do not introduce legacy repository/schema dependencies or compatibility layers unless a future explicit decision changes that direction.

Core baseline:

- Person belongs to Family;
- shared meals use one MealEvent with person-specific MealParticipant and Serving rows;
- safety and mandatory nutrition rules are deterministic and cannot be bypassed by learned ranking;
- Food/Recipe composition is versioned for reproducible Serving/recommendation calculations;
- DailyHealthState/DailyNutritionState are derived and recalculable;
- recommendation history/feedback are audit evidence, not authoritative meal-plan state;
- practical, pantry and commercial source data are operational state separate from nutrition composition;
- API namespace is `/api/...`, not `/api/v1`;
- web target is React + TypeScript + Vite;
- multilingual, responsive desktop/tablet/mobile and Light/Dark/System appearance remain product requirements.

## Mandatory workflow

Authoritative decision: `docs/decisions/ADR-007-development-workflow-and-ci.md`.

For every non-trivial increment:

1. verify the exact current `main` SHA;
2. create one focused branch from that exact SHA;
3. implement code, migration when needed, tests and relevant documentation together;
4. run every local validation gate for each affected application/package;
5. require zero-warning migration/static-analysis/test/build results;
6. open a PR only after explicit local green confirmation;
7. verify every relevant GitHub Actions workflow on the exact PR head SHA;
8. confirm the PR remains mergeable and its head SHA is unchanged;
9. squash-merge guarded by the tested head SHA;
10. verify `merged=true` and the resulting exact `main` SHA;
11. only then create the next branch and refresh this file.

Never develop directly on `main`, merge an untested head, or treat CI from an earlier SHA as validation of a later SHA.

## Local validation

### API/backend

No schema change:

```powershell
cd D:\Python\nutriflow-ai-v2
python -m alembic check

cd apps\api
python -m ruff check .
python -m pytest -q
```

Schema-changing branch:

```powershell
cd D:\Python\nutriflow-ai-v2
python -m alembic upgrade head
python -m alembic current
python -m alembic check

cd apps\api
python -m ruff check .
python -m pytest -q
```

Backend baseline: Python >=3.13, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, psycopg 3.x, pytest warnings as errors, Ruff target `py313`.

### Web

For branches affecting `apps/web`, web contracts or Web CI:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\web
npm install --no-package-lock --ignore-scripts
npm run test
npm run build
```

`npm run build` includes strict TypeScript checking. Web CI pins npm 11.12.1 because the GitHub runner npm 10.9.8 install path failed during PR #25 validation. No npm lockfile is committed yet; production hardening must add one and move CI to `npm ci`.

## Last integrated checkpoint

PR #25 integrated the first real responsive web recommendation vertical slice.

Exact integrated baseline:

```text
main SHA:          a18b61f0d6512c3a91f99d8f34e2e2c3e3fb2808
schema head:       a7c4e9f2b6d1
API test baseline: 94 tests
Web test baseline: 7 tests
```

PR #25 was locally validated, then CI exposed an npm 10.9.8 runner install failure. Web CI was pinned to npm 11.12.1, and both API CI and Web CI passed on exact head `0220d45564c017853ef38c2c277f0854d74ce0fa` before guarded squash merge.

Integrated end-to-end flow:

```text
GET  /api/families/{family_id}/persons
POST /api/persons/{person_id}/meal-recommendations/practical
POST /api/recommendation-options/{option_id}/decision
```

The web app can select a Person, submit practical context, display eligible/excluded recommendations plus commercial offers, and accept/reject persisted options. It is responsive, pt-PT/en, Light/Dark/System, and backed by separate Web CI.

Current integrated UI limitation: it still exposes DailyNutritionState and composition UUID inputs because no server-authoritative planning bootstrap was available at PR #25 merge time.

Detailed references:

- `docs/ux/web-recommendation-vertical-slice.md`;
- ADR-030;
- `apps/web/README.md`;
- `docs/domain/practical-recommendation-orchestration-api.md`;
- ADR-029.

## Current feature branch

Current branch:

```text
feature/web-planning-bootstrap-api
```

Merge base:

```text
a18b61f0d6512c3a91f99d8f34e2e2c3e3fb2808
```

Schema head remains:

```text
a7c4e9f2b6d1
```

No database migration is required.

Expected complete validation baseline after this branch:

```text
API: Alembic metadata clean, Ruff clean, 100 pytest tests
Web: unchanged integrated 7 Vitest tests
```

No PR may be opened until this exact branch receives explicit local green confirmation for the API gates.

### Current branch scope

This branch adds the read-only planning bootstrap boundary required to remove technical state/composition IDs from the normal web flow:

```text
GET /api/persons/{person_id}/planning-bootstrap?scheduled_at=<timezone-aware instant>
```

Implemented:

- timezone-aware `scheduled_at` is mandatory;
- planning date is derived in the persisted Person timezone;
- latest persisted DailyNutritionState for that local date is selected deterministically;
- missing DailyNutritionState is returned as `null`, never invented by the browser;
- active global and same-Family FoodItem/Recipe objects are discoverable;
- other-Family and inactive catalogue objects are excluded;
- Food composition selection requires `effective_at <= scheduled_at` and returns the latest eligible snapshot;
- Recipe composition selection requires `computed_at <= scheduled_at` and returns the latest eligible snapshot;
- future composition evidence is not exposed as current planning evidence;
- response includes persisted composition IDs plus display/reference metadata needed by the UI;
- recommendation trust boundaries remain unchanged: the browser still references persisted evidence rather than submitting nutrition totals;
- six API tests cover local date/latest state, Family isolation/catalogue scope, Food/Recipe as-of selection, missing-state semantics and naive-time rejection.

Authoritative current-branch docs:

- `docs/domain/web-planning-bootstrap-api.md`;
- `docs/decisions/ADR-031-web-planning-bootstrap-discovers-persisted-state-and-composition.md`;
- `docs/domain/implementation-status.md`.

## Current migration tail

```text
a7c4e9f2b6d1  commercial source opening windows and offers
f6b3d8e1a5c2  quantity-aware Family pantry stock lots
e5a2c7d9f4b1  Family-scoped meal candidate availability
d4f8a1b2c6e9  MealEvent Family-scoped idempotency
c3e7f9a1b5d2  recommendation run/option/feedback
```

Earlier revisions remain authoritative in `database/migrations/versions/`. Never guess a new revision; inspect actual heads/current state before adding migrations.

## Safety and correctness invariants

Preserve these across future work:

- mandatory adverse reactions and mandatory constraints run before ranking;
- learned/ML ranking can reorder eligible candidates only;
- missing candidate nutrient data cannot be interpreted as zero for a mandatory maximum;
- unsupported mandatory semantics and unsafe required conversions fail closed;
- no inferred density;
- Serving/recommendation decisions preserve exact versioned composition provenance;
- recommendation and bootstrap APIs reference persisted evidence rather than client-authored nutrition totals;
- planning bootstrap preserves Family isolation, excludes inactive catalogue objects and never uses future composition evidence for an earlier instant;
- practical source alternatives use any-source semantics and preserve unknown vs explicit unavailability;
- a practical scheduled instant cannot silently use nutrition state from another local day;
- commercial price/availability cannot override safety eligibility;
- web presentation must not reproduce or weaken backend eligibility/safety logic;
- ineligible recommendation options cannot be materialized;
- rejected decisions cannot create meal state;
- DailyNutritionState remains derived from authoritative meal history;
- shared meals retain person-specific portions and safety evaluation;
- retries/replacements remain idempotent only where explicitly supported;
- warnings are treated as failures, not suppressed casually.

Known follow-up: bootstrap intentionally returns `daily_nutrition_state=null` when the local date has no persisted state. Automatic refresh and NutritionTarget selection remain a separate policy increment.

## Implemented capability map

Use `docs/domain/implementation-status.md` as the compact status map. Key current references include:

- `docs/domain/adaptive-meal-recommendation.md`;
- `docs/domain/recommendation-feedback-model.md`;
- `docs/domain/recommendation-to-meal-plan.md`;
- `docs/domain/recommendation-practical-context.md`;
- `docs/domain/persisted-practical-availability.md`;
- `docs/domain/pantry-stock-shopping-requirements.md`;
- `docs/domain/restaurant-delivery-commercial-context.md`;
- `docs/domain/planning-api-vertical-slice.md`;
- `docs/domain/recommendation-decision-api.md`;
- `docs/domain/practical-recommendation-orchestration-api.md`;
- `docs/domain/web-planning-bootstrap-api.md`;
- `docs/ux/web-recommendation-vertical-slice.md`.

Durable decisions are under `docs/decisions/`; ADR-007 governs workflow.

## Next planned increments

After the current bootstrap API branch is locally green, PR-tested and merged:

1. wire `apps/web` to planning bootstrap, remove manual DailyNutritionState/composition UUID entry and replace it with normal named candidate selection;
2. add authentication and explicit Family/Person authorization context before real multi-user deployment;
3. commit an npm lockfile and switch Web CI to `npm ci` before production deployment;
4. expand the web app into profile/goals/constraints/preferences, daily plan/history and pantry/shopping vertical slices;
5. persist shopping-list lifecycle when UI workflows require durable shopping state;
6. add background/event-driven DailyNutritionState refresh and explicit target-selection policy;
7. harden request idempotency/concurrent decision races;
8. expose shared-family recommendation/decision API and UI boundaries;
9. add provider connectors/live freshness and basket/order lifecycle;
10. add learned ranking only after deterministic safety/practical/nutrition layers remain authoritative.

Any deliberate roadmap reordering must update this file and `docs/domain/implementation-status.md` together.

## Resume procedure

1. read this file;
2. read ADR-007;
3. read `docs/domain/implementation-status.md`;
4. inspect current branch, `git status`, `git log -1`, branch tracking and remote compare;
5. inspect actual Alembic heads/current state;
6. verify whether the exact active head already received local green validation;
7. do not open/merge a PR unless the exact head satisfies the workflow;
8. after merge, verify the new exact `main`, create the next focused branch, and refresh this checkpoint.
