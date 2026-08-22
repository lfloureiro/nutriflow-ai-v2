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

PR #31 enriched the explicit development demo Family with representative Family Home data and was locally approved, API/Web CI-green on the exact head and squash-merged.

Exact integrated baseline:

```text
main SHA:        e95270a4372aa767bded205cdb9f536480cecc27
schema head:     a7c4e9f2b6d1
API tests:       107
Web tests:       14
```

Integrated demo presentation data now includes four synthetic Family members, varied current-day health/nutrition evidence and three current-day Family meals. The seed remains explicit, idempotent, isolated and never auto-runs.

## Current feature branch

```text
feature/web-person-overview
```

Merge base:

```text
e95270a4372aa767bded205cdb9f536480cecc27
```

No schema or backend behavior change.

PR #32 is open for this branch. Its original local/CI validation applied to the earlier head `2f38a70a8324cd04199486c36c54e68f1df45929`. A subsequent visual review found raw backend meal enum labels in the Person overview, so the branch changed after that validation. The current head must receive fresh local green confirmation and fresh exact-head CI before merge.

Current scope:

- implement the first real Person drill-down from Family Home and `Pessoas`;
- keep primary Family navigation unchanged;
- make direct `Pessoas` navigation open the Family member list;
- make Person cards on `Início` open that Person directly;
- add Person secondary navigation: `Visão geral`, `Nutrição`, `Atividade`, `Saúde`, `Histórico`, `Perfil`;
- implement `Visão geral` using only current persisted evidence from the existing Family dashboard read model;
- show energy consumed/remaining, steps/active energy, weight/7-day trend, sleep/resting HR and current-day Person meals;
- filter Family meal agenda by persisted `participant_person_ids` only;
- localize known meal types/statuses for presentation instead of exposing raw enum values such as `lunch`, `planned` and `completed`;
- preserve unknown enum values unchanged rather than guessing a translation;
- keep missing evidence explicit rather than falling back or inserting zero;
- keep the other secondary sections as explicit lightweight placeholders until focused read models/screens are implemented;
- do not invent a health score, medical interpretation, nutrition targets or historical time series;
- do not add a chart until a future Person read model supplies an actual time series.

Expected validation baseline after the meal-label follow-up:

```text
API: Alembic metadata clean, Ruff clean, 107 pytest tests
Web: 18 Vitest tests, strict TypeScript check, production Vite build
```

Authoritative branch documentation:

- `docs/ux/person-overview.md`;
- `docs/ux/frontend-information-architecture.md`;
- `docs/ux/family-home-shell.md`;
- `docs/decisions/ADR-034-family-first-progressive-disclosure-web-navigation.md`;
- `docs/domain/implementation-status.md`.

Do not merge PR #32 until the exact current branch head receives explicit local green confirmation and exact-head API/Web CI is green.

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

The current demo Family is intentionally useful for Person-overview visual checks because members have different values and selected missing fields.

Repeated recommendation smoke tests can create additional genuine planned MealEvents in the persistent development database. The Person overview intentionally does not hide or deduplicate distinct authoritative MealEvents. A dedicated explicit demo reset/cleanup mechanism is a separate development-data concern and should not be implemented as presentation filtering.

## Current frontend structure

```text
Início
  -> Person card -> Person / Visão geral

Refeições
  -> practical recommendation flow

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
- Person overview only presents dashboard evidence and Person meal participation;
- distinct persisted MealEvents are not hidden by client-side deduplication;
- missing dashboard evidence remains `null`, not zero;
- commercial price/availability cannot override nutrition safety;
- web does not reimplement backend safety/ranking;
- ineligible options cannot be materialized and rejection cannot create meal state;
- shared meals keep Person-specific portions/safety checks;
- demo data remains explicit, synthetic, isolated, identifiable and never auto-seeded;
- warnings remain failures rather than suppressions.

Known limitations:

- Family UUID is development context, not authorization;
- detailed Person section read models are not yet implemented;
- persistent demo databases can accumulate accepted recommendation MealEvents until an explicit reset/cleanup path is added;
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

After this branch is revalidated, PR-tested, visually checked and merged:

1. add an explicit development-demo reset/cleanup path so repeated recommendation smoke tests do not permanently clutter the fixed demo Family;
2. implement Family Meals `Hoje` and `Semana` before the recommendation subflow;
3. add shared-meal drill-down with Person-specific portions;
4. add dedicated Person Nutrition/Activity/Health/History read models/screens;
5. add Person profile/goals/constraints/preferences screens;
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
