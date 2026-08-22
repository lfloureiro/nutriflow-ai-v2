# NutriFlow AI v2 development continuity

This document is the handover entry point for resuming NutriFlow AI v2 development. Repository state, migrations, tests, domain/UX docs and ADRs are authoritative when they differ from conversation history.

## Product and architecture baseline

NutriFlow AI v2 is standalone. Core invariants:

- Person belongs to Family;
- shared meals use one MealEvent with Person-specific MealParticipant and Serving rows;
- hard safety and mandatory nutrition rules run before ranking/ML;
- Food/Recipe composition is versioned with exact provenance;
- DailyHealthState/DailyNutritionState are derived and recalculable;
- recommendation history/feedback are audit evidence, not authoritative meal-plan state;
- API namespace is `/api/...`;
- web is React + TypeScript + Vite, responsive, pt-PT/en and Light/Dark/System;
- frontend is Family-first with progressive disclosure per ADR-034.

## Mandatory workflow

Authoritative decision: `docs/decisions/ADR-007-development-workflow-and-ci.md`.

For each non-trivial increment:

1. resolve exact current `main` SHA;
2. create one focused branch from that exact SHA;
3. implement code, tests, migration when needed and docs together;
4. run all relevant local gates with zero warnings/errors;
5. open PR only after explicit local green confirmation;
6. verify all relevant GitHub Actions on the exact PR head;
7. confirm mergeability/head unchanged;
8. squash-merge guarded by expected head SHA;
9. verify merged PR and exact new `main` SHA;
10. only then start the next branch.

## Validation commands

API/backend:

```powershell
cd D:\Python\nutriflow-ai-v2
python -m alembic check

cd apps\api
python -m ruff check .
python -m pytest -q
```

Web:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\web
npm install --no-package-lock --ignore-scripts
npm run test
npm run build
```

## Last integrated checkpoint

PR #32 added the first lightweight Person overview drill-down and was squash-merged.

```text
main SHA:        715ce09bc2034d6f88165f288b2d79321bdd4599
schema head:     a7c4e9f2b6d1
API tests:       107
Web tests:       16
```

Integrated frontend now includes:

```text
Início
Refeições
Pessoas
  -> Person
       ├── Visão geral
       ├── Nutrição      placeholder
       ├── Atividade     placeholder
       ├── Saúde         placeholder
       ├── Histórico     placeholder
       └── Perfil        placeholder
Casa
Mais
```

## Current feature branch

```text
fix/web-person-meal-labels
```

Merge base:

```text
715ce09bc2034d6f88165f288b2d79321bdd4599
```

No schema/API/backend behavior change.

Scope:

- fix raw backend enum values visible in Person meal rows;
- localize known meal types/statuses (`lunch` -> `Almoço`, `planned` -> `Planeada`, `completed` -> `Concluída`, etc.);
- preserve unknown values unchanged instead of guessing;
- keep distinct persisted MealEvents as distinct rows;
- document that repeated recommendation smoke tests can accumulate genuine planned MealEvents in the persistent demo database.

Expected validation baseline:

```text
API: Alembic metadata clean, Ruff clean, 107 pytest tests
Web: 18 Vitest tests, strict TypeScript check, production Vite build
```

Do not open/merge a PR for this branch until the exact current head is locally green.

## Demo-data observation from visual review

A Person overview screenshot showed several 11:14 planned meals with alternating accepted dishes. These are separate persisted MealEvents accumulated by earlier recommendation smoke tests, not duplicate rendering of one event.

The UI must not hide authoritative rows just because time/title repeat. Add an explicit demo reset/cleanup path in a separate focused increment so the fixed synthetic Family can be returned to a clean known state without presentation-layer deduplication.

## Safety/correctness invariants

Preserve:

- hard reactions/mandatory constraints before ranking;
- missing mandatory nutrient data fails closed;
- exact versioned composition provenance;
- browser does not author nutrition totals or choose evidence versions;
- Family/Person dashboard missing evidence remains `null`, never zero;
- Person overview only presents persisted evidence and meal participation;
- distinct persisted MealEvents remain distinct;
- web does not reproduce backend safety/ranking;
- demo data stays explicit, synthetic, identifiable and never auto-seeded;
- warnings remain failures.

Known limitations:

- Family UUID remains development context pending authentication/authorization;
- detailed Person read models are not yet implemented;
- persistent demo databases can accumulate accepted recommendation MealEvents until explicit reset is added;
- `Casa` is not yet functional;
- no URL/deep-link router yet;
- missing real DailyNutritionState is not automatically recalculated by bootstrap/dashboard;
- request-level/concurrent recommendation-decision idempotency is still pending;
- npm lockfile / `npm ci` hardening is pending;
- recommendation `datetime-local` still follows browser timezone.

## Migration tail

```text
a7c4e9f2b6d1  commercial source opening windows and offers
f6b3d8e1a5c2  quantity-aware Family pantry stock lots
e5a2c7d9f4b1  Family-scoped meal candidate availability
d4f8a1b2c6e9  MealEvent Family-scoped idempotency
c3e7f9a1b5d2  recommendation run/option/feedback
```

## Next planned increments

After this fix is validated and merged:

1. explicit development-demo reset/cleanup for accumulated smoke-test state;
2. Family Meals `Hoje` and `Semana` before recommendation;
3. shared-meal drill-down with Person-specific portions;
4. dedicated Person Nutrition/Activity/Health/History read models/screens;
5. Person profile/goals/constraints/preferences;
6. pantry/shopping UI;
7. authentication/authorization;
8. npm lockfile + `npm ci` hardening;
9. provider/live/basket/order and later learned ranking.
