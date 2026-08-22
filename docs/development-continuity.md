# NutriFlow AI v2 development continuity

This document is the handover entry point for resuming NutriFlow AI v2 development. Repository state, migrations, tests, domain/UX docs and ADRs are authoritative when they differ from conversation history.

## Product and architecture baseline

NutriFlow AI v2 is standalone. Do not introduce legacy repository/schema dependencies or compatibility layers unless an explicit future decision changes that direction.

Core invariants:

- Person belongs to Family;
- shared meals use one MealEvent with Person-specific MealParticipant and Serving rows;
- hard safety and mandatory nutrition rules are deterministic and cannot be bypassed by ranking/ML;
- Food/Recipe composition is versioned and exact composition provenance is retained;
- DailyHealthState/DailyNutritionState are derived and recalculable;
- recommendation history/feedback are audit evidence, not authoritative meal-plan state;
- practical/pantry/commercial state is separate from nutrition composition;
- API namespace is `/api/...`, not `/api/v1`;
- web is React + TypeScript + Vite, responsive, pt-PT/en and Light/Dark/System;
- frontend direction is Family-first with progressive disclosure, per ADR-034.

## Mandatory workflow

Authoritative decision: `docs/decisions/ADR-007-development-workflow-and-ci.md`.

For each non-trivial increment:

1. resolve exact current `main` SHA;
2. create one focused branch from that exact SHA;
3. implement code, migration when needed, tests and docs together;
4. run all relevant local gates;
5. require zero-warning migration/static-analysis/test/build results;
6. open PR only after explicit local green confirmation;
7. verify every relevant GitHub Actions workflow on the exact PR head SHA;
8. confirm mergeability and unchanged head;
9. squash-merge guarded by expected head SHA;
10. verify merged PR and exact resulting `main` SHA;
11. only then create the next branch and refresh this file.

Never develop directly on `main`, merge an untested head or treat CI from another SHA as validation.

## Validation commands

API/backend:

```powershell
cd D:\Python\nutriflow-ai-v2
python -m alembic check

cd apps\api
python -m ruff check .
python -m pytest -q
```

Schema-changing branches additionally run `alembic upgrade head` and `alembic current`.

The API pytest fixture clears application tables inside the test transaction and rolls the outer transaction back afterwards, so committed demo/browser data cannot contaminate tests.

Web:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\web
npm install --no-package-lock --ignore-scripts
npm run test
npm run build
```

Web CI pins npm 11.12.1. A committed lockfile and `npm ci` are still required before production deployment.

## Last integrated checkpoint

PR #30 added the visible Family-first application shell and Family Home. It was locally green, browser-smoke-tested, API/Web CI-green on the exact head and squash-merged.

Exact integrated baseline:

```text
main SHA:        e5c52531dcc7397592643ea712bf9b1d90e00bbd
schema head:     a7c4e9f2b6d1
API tests:       106
Web tests:       14
```

Integrated frontend:

```text
Início      lightweight Family Home
Refeições   practical recommendation flow
Pessoas     Family member selection
Casa        pantry/shopping placeholder
Mais        locale, appearance, development Family context
```

Desktop uses compact side navigation; mobile uses bottom navigation. Home consumes `GET /api/families/{family_id}/dashboard` and keeps missing evidence explicit.

## Current feature branch

```text
feature/demo-family-dashboard-data
```

Merge base:

```text
e5c52531dcc7397592643ea712bf9b1d90e00bbd
```

No schema change and no production-domain behavior change.

Current scope:

- enrich the explicit development demo dataset so the new Family Home can be visually evaluated with realistic variation;
- retain the existing fixed demo Family and primary `Pessoa Demo` planning identity;
- add three synthetic Family members: `Marta Demo`, `Rui Demo`, `Inês Demo`;
- add current-day synthetic DailyHealthState variation for all four members;
- add DailyNutritionState summaries for three members while deliberately leaving `Inês Demo` without nutrition state;
- deliberately leave selected health fields missing for some members so the UI exercises `Sem dados` states;
- add three deterministic current-day MealEvents: completed breakfast, planned lunch and planned shared dinner;
- add deterministic MealParticipants so the Home exercises participant names and shared-meal presentation;
- preserve the primary demo recommendation fixture, preference and mandatory sodium exclusion;
- preserve explicit, idempotent, isolated, development-only seed semantics from ADR-033;
- preserve the original primary Person DailyNutritionState identity so existing local seeded databases upgrade cleanly by rerunning the command.

Expected validation baseline:

```text
API: Alembic metadata clean, Ruff clean, 107 pytest tests
Web: 14 Vitest tests, strict TypeScript check, production Vite build
```

Authoritative branch documentation:

- `docs/domain/development-demo-dataset.md`;
- `docs/decisions/ADR-033-development-demo-data-is-explicit-idempotent-and-isolated.md`;
- `docs/ux/family-home-shell.md`;
- `docs/domain/implementation-status.md`.

Do not open a PR until the exact branch head receives explicit local green confirmation.

## Demo execution

The demo seed remains explicit:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\api
python -m app.demo_seed
```

Fixed demo Family ID:

```text
11111111-1111-4111-8111-111111111111
```

Expected current output includes four members, three current-day meals and six planning candidates. Rerunning the seed updates/reuses the reserved current-date rows; it does not delete unrelated data and never runs automatically from the API or web app.

The current Family Home should then display:

- four Person cards with different nutrition/activity/weight/sleep states;
- intentional missing nutrition/weight/sleep evidence on selected cards;
- a completed 08:00 breakfast;
- a planned 13:00 lunch for two members;
- a planned 20:00 shared Family dinner.

## Safety and correctness invariants

Preserve:

- hard reactions/mandatory constraints before ranking;
- missing mandatory nutrient data fails closed;
- unsupported mandatory semantics and unsafe required conversions fail closed;
- no inferred density;
- exact versioned composition provenance;
- browser does not author nutrition totals or choose state/composition versions itself;
- planning bootstrap preserves Family isolation and as-of version selection;
- Family dashboard returns persisted evidence without medical interpretation or invented health scores;
- missing dashboard evidence remains `null`, not zero;
- commercial price/availability cannot override nutrition safety;
- web does not reimplement backend safety/ranking;
- ineligible options cannot be materialized and rejection cannot create meal state;
- shared meals keep Person-specific portions/safety checks;
- demo data remains explicit, synthetic, isolated, identifiable and never auto-seeded;
- warnings remain failures rather than suppressions.

Known limitations:

- Family UUID is development context, not authorization;
- Person detail is not yet implemented;
- `Casa` is not yet functional;
- no URL/deep-link router yet;
- missing real DailyNutritionState is not automatically recalculated by bootstrap/dashboard;
- recommendation decision request-level/concurrent idempotency is not yet guaranteed;
- npm lockfile / `npm ci` hardening is still pending;
- recommendation `datetime-local` still uses the browser timezone rather than a Person-local wall-time control.

## Migration tail

```text
a7c4e9f2b6d1  commercial source opening windows and offers
f6b3d8e1a5c2  quantity-aware Family pantry stock lots
e5a2c7d9f4b1  Family-scoped meal candidate availability
d4f8a1b2c6e9  MealEvent Family-scoped idempotency
c3e7f9a1b5d2  recommendation run/option/feedback
```

Never guess the next migration revision; inspect the actual migration directory and Alembic state first.

## Next planned increments

After this branch is locally green, PR-tested, visually checked and merged:

1. implement the Person overview and secondary navigation;
2. implement Family Meals `Hoje` and `Semana` before the recommendation subflow;
3. add shared-meal drill-down with Person-specific portions;
4. add dedicated Nutrition/Activity/Health/History screens;
5. add profile/goals/constraints/preferences screens;
6. add pantry/shopping UI and durable shopping-list lifecycle;
7. add authentication and explicit Family/Person authorization before real multi-user deployment;
8. commit npm lockfile and switch CI to `npm ci` before production;
9. continue provider/live/basket/order and later learned-ranking work.

## Resume procedure

1. read this file and ADR-007;
2. inspect current `main`, active branch and compare state;
3. inspect migration heads/current state;
4. inspect relevant app validation commands and CI workflows;
5. confirm whether the exact current branch head has explicit local green validation;
6. do not PR/merge an unvalidated head;
7. after merge, verify new exact `main` before creating the next branch.
