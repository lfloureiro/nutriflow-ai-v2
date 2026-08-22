# NutriFlow AI v2 development continuity

This document is the handover entry point for resuming NutriFlow AI v2 development. Repository state, migrations, tests, domain/UX docs and ADRs are authoritative when they differ from conversation history.

## Product and architecture baseline

NutriFlow AI v2 is standalone. Do not introduce legacy repository/schema dependencies or compatibility layers unless an explicit future decision changes that direction.

Core invariants:

- Person belongs to Family;
- shared meals use one MealEvent with person-specific MealParticipant and Serving rows;
- hard safety and mandatory nutrition rules are deterministic and cannot be bypassed by ranking/ML;
- Food/Recipe composition is versioned and exact composition provenance is retained;
- DailyHealthState/DailyNutritionState are derived and recalculable;
- recommendation history/feedback are audit evidence, not authoritative meal-plan state;
- practical/pantry/commercial state is separate from nutrition composition;
- API namespace is `/api/...`, not `/api/v1`;
- web is React + TypeScript + Vite, responsive, pt-PT/en and Light/Dark/System.

Frontend product direction is now explicitly family-first and progressively disclosed: lightweight Family Home, Person drill-down and Meals as a parallel primary workflow. Detailed decision: ADR-034 and `docs/ux/frontend-information-architecture.md`.

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

Web:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\web
npm install --no-package-lock --ignore-scripts
npm run test
npm run build
```

Web CI pins npm 11.12.1. A committed lockfile and `npm ci` are still required before production deployment.

## Last integrated checkpoint

PR #28 added the explicit idempotent development demo dataset and was locally green, API/Web CI-green on the exact head, browser-smoke-tested and squash-merged.

Exact integrated baseline:

```text
main SHA:        6d232fd6217fca7853ddefce0273f832ce7488cc
schema head:     a7c4e9f2b6d1
API tests:       103
Web tests:       10
```

The local demo seed remains explicit:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\api
python -m app.demo_seed
```

Fixed demo Family ID:

```text
11111111-1111-4111-8111-111111111111
```

## Current feature branch

```text
feature/web-family-home-architecture
```

Merge base:

```text
6d232fd6217fca7853ddefce0273f832ce7488cc
```

No schema change.

Current scope:

- establish the long-term web information architecture before expanding visual screens;
- prefer focused screens and drill-down over dense all-in-one dashboards;
- define primary navigation as Início, Refeições, Pessoas, Casa and Mais;
- define Family Home as the initial orientation screen;
- keep Meals as a parallel primary family workflow rather than making the meal planner the Home;
- define Person drill-down for overview, nutrition, activity, health, history and profile;
- add `GET /api/families/{family_id}/dashboard?on_date=...` as a compact server-authoritative Home read model;
- expose latest current-day DailyHealthState/DailyNutritionState per Family member without filling missing evidence;
- expose current local-day active MealEvents with participants;
- exclude cancelled/replaced meals from the normal Home agenda;
- add typed web contracts/client support for the Family dashboard endpoint;
- do not yet replace the existing recommendation screen with the new visual shell in this branch.

Expected validation baseline:

```text
API: Alembic metadata clean, Ruff clean, 106 pytest tests
Web: 11 Vitest tests, strict TypeScript check, production Vite build
```

Authoritative current-branch docs:

- `docs/ux/frontend-information-architecture.md`;
- `docs/domain/family-dashboard-read-model.md`;
- `docs/decisions/ADR-034-family-first-progressive-disclosure-web-navigation.md`;
- `docs/domain/implementation-status.md`.

Do not open a PR until the exact branch head receives explicit local green confirmation for both API and Web gates.

## Family Home API semantics

Endpoint:

```text
GET /api/families/{family_id}/dashboard?on_date=YYYY-MM-DD
```

When `on_date` is omitted, the server resolves today using the persisted Family timezone.

The endpoint returns:

- Family identity/name/timezone;
- dashboard local date;
- every Family member;
- latest DailyHealthState for that exact date, or `null`;
- latest DailyNutritionState for that exact date, or `null`;
- active current-day family meals and participant Person IDs.

It does not calculate an aggregate family health score or medical interpretation. Missing evidence remains missing.

## Frontend information architecture

Primary destinations:

```text
Início      family overview today
Refeições   today/week/recommendation/shared-meal drill-down
Pessoas     Person selection and individual drill-down
Casa        pantry and later shopping
Mais        settings/integrations/family administration
```

Person drill-down:

```text
Visão geral
Nutrição
Atividade
Saúde
Histórico
Perfil -> objetivos / restrições / preferências / integrações
```

Density rules:

- Family Home: compact member cards + today's meals + at most one prominent next action;
- Home normally has zero or one small chart;
- Person overview normally has at most one primary chart;
- more analytics belong on dedicated screens;
- desktop uses compact side navigation;
- mobile uses compact bottom navigation;
- missing evidence is unavailable/unknown, not zero.

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
- missing practical evidence remains unknown rather than unavailable;
- commercial price/availability cannot override nutrition safety;
- web does not reimplement backend safety/ranking;
- ineligible options cannot be materialized and rejection cannot create meal state;
- DailyNutritionState remains derived from authoritative meal history outside explicit synthetic development fixtures;
- shared meals keep person-specific portions/safety checks;
- demo data remains explicit, isolated, identifiable and never auto-seeded;
- warnings remain failures rather than suppressions.

Known limitations:

- Family UUID remains a development entrypoint because authentication/authorization is not implemented;
- bootstrap does not create a missing real DailyNutritionState;
- Family dashboard is a read model only and does not refresh missing derived states;
- recommendation decision request-level/concurrent idempotency is not yet guaranteed;
- npm lockfile / `npm ci` hardening is still pending.

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

After this branch is locally green, PR-tested and merged:

1. build the application shell and responsive primary navigation using the new information architecture;
2. implement the Family Home visually against the dashboard endpoint;
3. enrich the development demo data with representative health/activity and multiple Family members as needed for UI validation;
4. build Person overview and drill-down navigation;
5. move the existing recommendation UI under Refeições and add today/week family meal views;
6. add meal drill-down with shared meal and Person-specific portions;
7. add dedicated Nutrition/Activity/Health/History screens;
8. add profile/goals/constraints/preferences screens;
9. add authentication and explicit Family/Person authorization before real multi-user deployment;
10. harden npm dependency locking and then continue pantry/shopping/provider workflows.

## Resume procedure

1. read this file and ADR-007;
2. inspect current `main`, active branch and compare state;
3. inspect migration heads/current state;
4. inspect relevant app validation commands and CI workflows;
5. confirm whether the exact current branch head has explicit local green validation;
6. do not PR/merge an unvalidated head;
7. after merge, verify new exact `main` before creating the next branch.
