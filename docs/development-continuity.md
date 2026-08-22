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

Web:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\web
npm install --no-package-lock --ignore-scripts
npm run test
npm run build
```

Warnings are failures. The API pytest fixture isolates tests from committed development/demo data.

## Last integrated checkpoint

PR #33 added the Family meal-map workflow (`Refeições > Hoje / Semana / Recomendar`). It was explicitly locally approved, API/Web CI-green on exact head `52b1ba0e21fc4beffabdca7c6a9ae3d300f2f5b8`, and guarded squash-merged.

Exact integrated baseline:

```text
main SHA:        e0bdd8a9c8cc40f58ab67f14727ab134ac2156dc
schema head:     a7c4e9f2b6d1
API tests:       110
Web tests:       19
```

Integrated frontend now includes Family Home, Person selection/overview, Family meals Today/Week and the existing practical recommendation flow under `Refeições > Recomendar`.

## Current feature branch

```text
feature/web-family-meal-detail
```

Merge base:

```text
e0bdd8a9c8cc40f58ab67f14727ab134ac2156dc
```

No database migration.

Current scope:

- add `GET /api/families/{family_id}/meals/{meal_event_id}` as a read-only Family-scoped detail projection;
- expose persisted MealEvent summary, MealParticipants and each participant's persisted Servings;
- expose planned/served/consumed quantity and energy lifecycle values without recalculating them;
- return `404` for a missing/cross-Family meal ID;
- make meal rows in `Hoje`/`Semana` open a separate focused `Refeição` drill-down;
- preserve `Hoje` and `Semana` as compact orientation screens rather than expanding rows in place;
- show Family-local date/time, optional location, MealEvent status, participant names/statuses and Person-specific portions;
- show the most realized persisted Serving evidence for concise presentation: consumed, else served, else planned;
- keep missing Serving evidence explicit rather than inferring another Person's portion or zero;
- keep the browser out of nutrition/safety/ranking calculations;
- add deterministic/idempotent synthetic Serving fixtures to the existing demo meals so the drill-down is immediately testable;
- keep advanced explanation, alternatives/edit commands, nutrient breakdowns and safety-result rendering outside this increment.

Expected validation baseline after implementation:

```text
API: Alembic metadata clean, Ruff clean, 112 pytest tests
Web: 21 Vitest tests, strict TypeScript check, production Vite build
```

These counts are expectations only until the exact branch head is locally validated.

Authoritative branch documentation:

- `docs/domain/family-meals-read-model.md`;
- `docs/ux/family-meal-detail.md`;
- `docs/ux/family-meals-today-week.md`;
- `docs/ux/frontend-information-architecture.md`;
- `docs/decisions/ADR-034-family-first-progressive-disclosure-web-navigation.md`;
- `docs/domain/implementation-status.md`.

Do not open a PR until the exact current branch head receives explicit local green confirmation.

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

The demo includes four Family members and three current-day meals. Each of the ten demo MealParticipants now has a deterministic Person-specific Serving fixture, with different quantities across participants. This makes `Refeições > Hoje -> Refeição` directly testable after seeding.

`Semana` deliberately contains empty days because the API returns the complete requested local calendar range.

## Current frontend structure

```text
Início
  -> Person card -> Person / Visão geral
  -> Planear refeição -> Refeições / Recomendar

Refeições
  ├── Hoje        Family-local daily agenda
  │    -> Refeição -> participantes + porções individuais
  ├── Semana      Monday-Sunday Family map
  │    -> Refeição -> participantes + porções individuais
  └── Recomendar  practical recommendation flow

Pessoas
  -> Family member list
  -> Person
       ├── Visão geral   implemented
       ├── Nutrição      placeholder
       ├── Atividade     placeholder
       ├── Saúde         placeholder
       ├── Histórico     placeholder
       └── Perfil        placeholder

Casa
Mais
```

Density rules remain:

- one screen answers one primary question;
- Family Home remains compact;
- Family meals calendar uses readable vertical day sections instead of a dense seven-column planner;
- meal detail is a separate focused screen, not an expanded calendar row;
- Person overview remains compact and has at most one future primary chart;
- detailed analytics belong on dedicated sections;
- missing evidence is unavailable/unknown, never zero.

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
- Family meals calendar uses Family-local calendar boundaries and persisted participants only;
- Family meal detail uses persisted `MealEvent -> MealParticipant -> Serving` ownership and never infers portions across Persons;
- direct detail lookup is Family-scoped;
- Person overview only presents dashboard evidence and Person meal participation;
- missing evidence remains missing, not zero;
- commercial price/availability cannot override nutrition safety;
- web does not reimplement backend safety/ranking;
- ineligible options cannot be materialized and rejection cannot create meal state;
- shared meals keep Person-specific portions/safety checks even though the Family calendar summarizes the event once;
- demo data remains explicit, synthetic, isolated, identifiable and never auto-seeded;
- warnings remain failures rather than suppressions.

Known limitations:

- Family UUID is development context, not authorization;
- meal-detail explanation/alternatives/edit commands are not yet implemented;
- detailed Person section read models are not yet implemented;
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

1. add dedicated Person Nutrition/Activity/Health/History read models/screens;
2. add Person profile/goals/constraints/preferences screens;
3. add pantry/shopping UI and durable shopping-list lifecycle;
4. add authentication and explicit Family/Person authorization before real multi-user deployment;
5. commit npm lockfile and switch CI to `npm ci` before production;
6. add advanced meal explanation/alternatives/edit flows when their authoritative semantics are defined;
7. continue provider/live/basket/order and later learned-ranking work.

## Resume procedure

1. read this file and ADR-007;
2. inspect current `main`, active branch and compare state;
3. inspect migration heads/current state;
4. inspect relevant app validation commands and CI workflows;
5. confirm whether the exact current branch head has explicit local green validation;
6. do not PR/merge an unvalidated head;
7. after merge, verify new exact `main` before creating the next branch.
