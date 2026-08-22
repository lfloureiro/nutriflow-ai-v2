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

PR #29 defined the Family-first information architecture and added the Family dashboard read model. It was locally green, API/Web CI-green on the exact head and squash-merged.

Exact integrated baseline:

```text
main SHA:        3c8b349e5b43a7685dde9a616ca4e5b22e58cef5
schema head:     a7c4e9f2b6d1
API tests:       106
Web tests:       11
```

Integrated Family Home read model:

```text
GET /api/families/{family_id}/dashboard?on_date=YYYY-MM-DD
```

It returns current-day Family members, persisted DailyHealthState/DailyNutritionState evidence and active Family MealEvents without inventing health scores or filling missing evidence.

## Current feature branch

```text
feature/web-app-shell-family-home
```

Merge base:

```text
3c8b349e5b43a7685dde9a616ca4e5b22e58cef5
```

No schema change.

Current scope:

- replace the developer recommendation screen as the application entry point;
- implement the primary shell from ADR-034;
- desktop: compact left navigation;
- mobile: bottom navigation;
- destinations: Início, Refeições, Pessoas, Casa, Mais;
- render a lightweight Family Home against the Family dashboard endpoint;
- show compact Person cards with current nutrition/activity/weight/sleep evidence when available;
- show missing evidence explicitly rather than as zero;
- show today's active Family meals in one agenda;
- keep one prominent `Planear refeição` action;
- move the existing practical recommendation flow under `Refeições` and reuse the active Family context instead of asking for the Family UUID again;
- expose the first lightweight `Pessoas` list/selection state without implementing detailed Person analytics yet;
- keep `Casa` as an intentional placeholder for pantry/shopping;
- move language, appearance and development Family-context controls under `Mais`;
- preserve the existing backend authority boundary for planning state, composition versions, safety, eligibility and ranking;
- correct CSS load order so the bootstrap candidate-row overrides follow the base stylesheet.

Development Family context:

- authentication/authorization is still not implemented;
- a successfully loaded Family ID is stored in local storage;
- Vite development defaults to the fixed explicit demo Family ID only when no stored Family exists;
- production builds do not receive that demo default;
- the UI never seeds data automatically.

Expected validation baseline:

```text
API: Alembic metadata clean, Ruff clean, 106 pytest tests
Web: 14 Vitest tests, strict TypeScript check, production Vite build
```

Authoritative current-branch docs:

- `docs/ux/family-home-shell.md`;
- `docs/ux/frontend-information-architecture.md`;
- `docs/domain/family-dashboard-read-model.md`;
- `docs/decisions/ADR-034-family-first-progressive-disclosure-web-navigation.md`.

Do not open a PR until the exact branch head receives explicit local green confirmation for both API and Web gates.

## Demo execution

The demo seed remains explicit and idempotent:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\api
python -m app.demo_seed
```

Fixed demo Family ID:

```text
11111111-1111-4111-8111-111111111111
```

The shell may prefill/use this ID in Vite development, but it never creates the Family itself.

## Frontend navigation now being implemented

```text
Início      Family overview for today
Refeições   practical recommendation flow; later today/week/shared meal detail
Pessoas     Family member selection; later Person overview/drill-down
Casa        pantry and later shopping
Mais        language, appearance, integrations/admin later
```

Density rules remain:

- one screen answers one primary question;
- Home has compact member cards and meal agenda, no analytics grid;
- no aggregate health score;
- Person overview will have at most one primary chart;
- detailed analytics belong on dedicated screens;
- missing evidence is unknown/unavailable, never zero.

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
- demo data remains explicit, isolated, identifiable and never auto-seeded;
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

After this branch is locally green, PR-tested and merged:

1. enrich the development demo dataset with representative health/activity evidence and additional Family members for visual validation;
2. implement the Person overview and its secondary navigation;
3. implement Family meals Today/Week before the recommendation subflow;
4. add shared-meal drill-down with Person-specific portions;
5. add dedicated Nutrition/Activity/Health/History screens;
6. add profile/goals/constraints/preferences screens;
7. add pantry/shopping UI and durable shopping-list lifecycle;
8. add authentication and explicit Family/Person authorization before real multi-user deployment;
9. commit npm lockfile and switch CI to `npm ci` before production;
10. continue provider/live/basket/order and later learned-ranking work.

## Resume procedure

1. read this file and ADR-007;
2. inspect current `main`, active branch and compare state;
3. inspect migration heads/current state;
4. inspect relevant app validation commands and CI workflows;
5. confirm whether the exact current branch head has explicit local green validation;
6. do not PR/merge an unvalidated head;
7. after merge, verify new exact `main` before creating the next branch.
