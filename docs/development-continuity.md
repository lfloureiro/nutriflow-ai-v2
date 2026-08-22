# NutriFlow AI v2 development continuity

This document is the handover entry point for resuming NutriFlow AI v2 development in a later session. It records the current repository checkpoint, mandatory workflow, safety invariants and next planned steps so development can continue from the repository without relying on conversation history.

When details differ, repository state, code, migrations, tests, the relevant domain/UX document and ADR are authoritative.

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
- initial web target is React + TypeScript;
- multilingual, responsive web/mobile and Light/Dark/System appearance remain product requirements.

## Mandatory workflow

Authoritative decision: `docs/decisions/ADR-007-development-workflow-and-ci.md`.

Use this sequence for every non-trivial increment:

1. verify the exact current `main` SHA;
2. create one focused branch from that SHA;
3. implement code, migration when needed, tests and relevant documentation together;
4. run the relevant local validation gates for every affected application/package;
5. require all relevant migration/static-analysis/test/build gates to pass with zero warnings;
6. open a PR only after explicit local green confirmation;
7. verify every relevant GitHub Actions workflow on the exact PR head SHA;
8. confirm PR mergeability and unchanged head SHA;
9. squash-merge guarded by the tested head SHA;
10. verify the merged PR and resulting exact `main` SHA;
11. only then create the next branch;
12. refresh this continuity checkpoint on that next branch.

Never commit feature work directly to `main`. Never merge an untested head. CI for an earlier SHA does not validate a later SHA. Documentation is part of the Definition of Done.

## Local validation commands

### API/backend

For a schema-changing branch, from repository root:

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic check

cd apps\api
python -m ruff check .
python -m pytest -q
```

For a branch without schema changes, `alembic upgrade head/current` are optional, but `alembic check`, Ruff and the complete pytest suite remain required when the branch can affect the integrated product or CI configuration.

Current backend baseline:

- Python >= 3.13;
- FastAPI;
- SQLAlchemy 2.x;
- Alembic;
- PostgreSQL;
- psycopg 3.x;
- pytest warnings treated as errors;
- Ruff target `py313`, line length 100.

### Web

For a branch affecting `apps/web`, web contracts or Web CI:

```powershell
cd apps\web
npm install --no-package-lock --ignore-scripts
npm run test
npm run build
```

`npm run build` includes the strict TypeScript check before the Vite production build.

Current web baseline on the active feature branch:

- Node.js >= 22;
- React 19;
- TypeScript strict mode;
- Vite;
- Vitest;
- CSS design tokens and responsive layouts;
- Portuguese/English authored UI strings;
- Light/Dark/System appearance support.

The current bootstrap pins direct npm dependency versions but intentionally has no committed lockfile yet. This is temporary development debt documented in ADR-030. A committed lockfile and `npm ci` are required before production deployment.

## Last integrated checkpoint

PR #24 integrated the practical recommendation orchestration API.

Exact integrated baseline:

```text
main SHA:        55a2842b1dcd68541d3dccb73b8580daadf1a4c9
schema head:     a7c4e9f2b6d1
API test baseline: 94 tests
```

PR #24 was locally validated, passed API CI on the exact tested head and was squash-merged.

Integrated recommendation flow now includes:

```text
POST /api/persons/{person_id}/meal-recommendations
POST /api/persons/{person_id}/meal-recommendations/practical
POST /api/recommendation-options/{option_id}/decision
```

The practical endpoint loads Person schedule and operational evidence server-side, combines home/pantry/commercial sources with any-source semantics, preserves unknown-vs-unavailable distinction, enforces local planning-date alignment and persists the resulting recommendation run/options. The decision endpoint can then accept/modify/reject eligible persisted options and materialize accepted/modified options through normal meal state.

Detailed semantics: `docs/domain/planning-api-vertical-slice.md`, ADR-027, `docs/domain/recommendation-decision-api.md`, ADR-028, `docs/domain/practical-recommendation-orchestration-api.md`, ADR-029.

## Current feature branch

Current branch:

```text
feature/web-recommendation-vertical-slice
```

Merge base:

```text
55a2842b1dcd68541d3dccb73b8580daadf1a4c9
```

Schema head remains:

```text
a7c4e9f2b6d1
```

This branch has no database migration and must not change backend recommendation safety semantics.

Expected complete validation baseline:

```text
API: Alembic metadata clean, Ruff clean, 94 pytest tests
Web: 7 Vitest tests, strict TypeScript check, production Vite build
```

No PR should be opened until this exact branch head receives explicit local green confirmation for all of those relevant gates.

### Current branch scope

This branch creates the first real web application under `apps/web`.

Implemented on the branch:

- React + TypeScript + Vite bootstrap;
- strict TypeScript configuration;
- typed API boundary isolated under `src/api/`;
- local Vite `/api` proxy to FastAPI at `127.0.0.1:8000`;
- Family UUID -> Person loading through `GET /api/families/{family_id}/persons`;
- selected Person context and timezone display;
- explicit DailyNutritionState UUID input because no safe current-state discovery API exists yet;
- explicit Food/Recipe composition snapshot IDs and quantities because no catalogue/composition browse API exists yet;
- practical meal form with planning date/time, meal type, location, available minutes, kitchen state and practical source kinds;
- real practical recommendation request through `POST /api/persons/{person_id}/meal-recommendations/practical`;
- server-authoritative eligible/excluded options rendered without client-side re-ranking or safety logic;
- compact nutrition, server explanations/exclusion reason codes and active commercial offers;
- Accept/Reject actions over eligible persisted options via the recommendation decision API;
- accepted decision response reports resulting MealEvent/Serving materialization;
- Portuguese (`pt-PT`) and English authored strings behind translation keys;
- document `lang` follows the active locale;
- Light, Dark and System modes stored as browser presentation preference only;
- responsive desktop/tablet/mobile layout with visible keyboard focus and semantic form/status/error structure;
- seven Vitest unit tests: three API URL tests, two planning-helper tests and two i18n tests;
- separate `.github/workflows/web-ci.yml` running web tests and strict production build;
- `apps/web/README.md`, ADR-030 and UX documentation.

This is intentionally an integration/development UI rather than final onboarding. The server still requires explicit persisted DailyNutritionState and composition evidence, so UUID entry remains visible. The web must not guess those values.

Authoritative current-branch docs:

- `docs/ux/web-recommendation-vertical-slice.md`;
- `docs/decisions/ADR-030-react-vite-web-foundation.md`;
- `apps/web/README.md`;
- `docs/domain/implementation-status.md`.

### Current web dependency policy

Direct package versions are pinned. No npm lockfile is committed in this bootstrap branch.

Local and CI install with:

```text
npm install --no-package-lock --ignore-scripts
```

This avoids mutating the branch during the first toolchain-validation increment but is not the desired production state. Before deployment, add a committed lockfile in a focused hardening increment and change Web CI to `npm ci`.

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
- practical source alternatives use any-source semantics;
- missing practical source evidence remains distinct from explicit unavailability;
- a practical scheduled instant cannot silently use nutrition state from another local day;
- pantry quantity/yield evaluation fails explicitly when it cannot be performed safely;
- commercial offer/price evidence cannot override safety eligibility;
- web presentation must not reproduce, weaken or override backend eligibility/safety logic;
- web candidate/state selection must eventually be server-authoritative rather than guessed from timestamps or catalogue state;
- ineligible recommendation options cannot be materialized through decision APIs;
- rejected recommendation decisions cannot create meal state;
- historical recommendation/feedback evidence remains append-only;
- DailyNutritionState derives from authoritative meal history;
- Family-scoped catalogue/operational data cannot leak across Families;
- shared meals retain person-specific portions and safety evaluation;
- retries and plan replacement preserve idempotency and immutable history where the domain explicitly supports it;
- warnings are treated as failures rather than casually suppressed.

Current decision API limitation: request-level idempotency and concurrent duplicate suppression are not implemented. Do not infer retry safety from MealEvent idempotency infrastructure elsewhere in the domain.

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
- `docs/domain/planning-api-vertical-slice.md`;
- `docs/domain/recommendation-decision-api.md`;
- `docs/domain/practical-recommendation-orchestration-api.md`.

Web/UX foundation:

- `docs/ux/web-recommendation-vertical-slice.md`;
- ADR-030;
- `apps/web/README.md`.

Durable decisions are under `docs/decisions/`; ADR-007 governs workflow.

## Next planned increments

After the current web branch is locally green, PR-tested and merged:

1. add a safe Person planning-bootstrap/discovery API for current DailyNutritionState and eligible current Food/Recipe composition snapshots so the web UI no longer requires UUID entry;
2. replace UUID-oriented web inputs with normal searchable/selectable product UI using server-authoritative bootstrap data;
3. add authentication and explicit Family/Person authorization context before real multi-user deployment;
4. add a committed npm lockfile and switch Web CI to `npm ci` before production deployment;
5. expand the web app into profile/goals/constraints/preferences, daily plan/history and pantry/shopping vertical slices;
6. persist shopping-list lifecycle when UI workflows require durable shopping state;
7. add background/event-driven DailyNutritionState refresh and explicit target-selection policy;
8. harden request idempotency/concurrent decision races at write API boundaries;
9. expose shared-family recommendation/decision API and UI boundaries;
10. add provider connectors/live freshness, basket/order lifecycle and later learned ranking only after deterministic layers remain authoritative.

The immediate priority after the first web merge is usability: remove development UUID entry safely rather than widening backend domains again.

Any deliberate roadmap reordering must update both this file and `docs/domain/implementation-status.md`.

## Resume procedure for a later session

1. read this file;
2. read ADR-007;
3. read `docs/domain/implementation-status.md`;
4. inspect `git status`, current branch, `git log -1`, `git branch -vv` and remote state;
5. compare the active feature branch with `main`;
6. inspect actual Alembic heads/current state;
7. inspect the relevant application package/workflow and its local validation commands;
8. verify whether the exact branch head already received explicit local green validation;
9. do not open or merge a PR unless the exact active head satisfies the workflow;
10. after merge, verify new `main`, create the next focused branch, then update this file.

Repository state, tests and documentation are the source of truth. Conversation history is optional context only.
