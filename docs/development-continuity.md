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

API/backend branch:

```powershell
cd D:\Python\nutriflow-ai-v2
python -m alembic check

cd apps\api
python -m ruff check .
python -m pytest -q
```

Schema-changing branches additionally run `alembic upgrade head` and `alembic current`.

Web branch:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\web
npm install --no-package-lock --ignore-scripts
npm run test
npm run build
```

Web CI pins npm 11.12.1. A committed lockfile and `npm ci` are still required before production deployment.

## Last integrated checkpoint

PR #26 added server-authoritative planning bootstrap discovery and was locally green, CI-green on the exact head, and squash-merged.

Exact integrated baseline:

```text
main SHA:        3ae41826a873d428a112c4060c95bea0856ffbbb
schema head:     a7c4e9f2b6d1
API tests:       100
Web tests:       7
```

Integrated planning API flow:

```text
GET  /api/persons/{person_id}/planning-bootstrap?scheduled_at=...
POST /api/persons/{person_id}/meal-recommendations/practical
POST /api/recommendation-options/{option_id}/decision
```

The bootstrap endpoint resolves the Person local date, latest persisted DailyNutritionState for that date, and current global/same-Family Food/Recipe composition evidence. Missing daily state remains `null`; future composition evidence is never selected.

Detailed semantics: `docs/domain/web-planning-bootstrap-api.md`, ADR-031.

## Current feature branch

```text
feature/web-bootstrap-selection-ui
```

Merge base:

```text
3ae41826a873d428a112c4060c95bea0856ffbbb
```

No schema change. No backend recommendation-rule change.

Current scope:

- web typed contracts/client call planning bootstrap;
- selected Person + scheduled instant automatically load bootstrap evidence;
- DailyNutritionState UUID input removed from the UI;
- composition UUID inputs removed from the UI;
- user selects named Food/Recipe candidates with brand/reference serving/energy display;
- candidate quantity/unit initialize from server reference values and remain editable;
- technical composition IDs stay internal and are sent to the existing recommendation API;
- duplicate selected composition IDs are disabled;
- Person/time changes invalidate old bootstrap, candidate, recommendation and decision state;
- missing DailyNutritionState and empty catalogue are explicit and recommendation is disabled;
- backend remains authoritative for eligibility, exclusions, ranking and practical/commercial rules.

Expected validation baseline:

```text
API: Alembic metadata clean, Ruff clean, 100 pytest tests
Web: 10 Vitest tests, strict TypeScript check, production Vite build
```

Authoritative current-branch docs:

- `docs/ux/web-bootstrap-selection-flow.md`;
- `docs/decisions/ADR-032-web-planning-uses-server-bootstrap-evidence.md`;
- `docs/domain/implementation-status.md`.

Do not open a PR until the exact current branch head receives explicit local green confirmation for both API and web gates.

## Safety and correctness invariants

Preserve:

- hard reactions/mandatory constraints before ranking;
- missing mandatory nutrient data fails closed;
- unsupported mandatory semantics and unsafe required conversions fail closed;
- no inferred density;
- exact versioned composition provenance;
- browser does not author nutrition totals or choose state/composition versions itself;
- planning bootstrap preserves Family isolation and as-of version selection;
- missing practical evidence remains unknown rather than unavailable;
- commercial price/availability cannot override nutrition safety;
- web does not reimplement backend safety/ranking;
- ineligible options cannot be materialized and rejection cannot create meal state;
- DailyNutritionState remains derived from authoritative meal history;
- shared meals keep person-specific portions/safety checks;
- warnings remain failures rather than suppressions.

Known limitations:

- Family UUID remains a development entrypoint because authentication/authorization is not implemented;
- bootstrap does not create a missing DailyNutritionState;
- recommendation decision request-level/concurrent idempotency is not yet guaranteed.

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

1. authentication and explicit Family/Person authorization context;
2. committed npm lockfile and Web CI `npm ci` hardening before production;
3. web profile/goals/constraints/preferences and daily plan/history slices;
4. pantry/shopping UI plus durable shopping-list lifecycle when needed;
5. background/event-driven DailyNutritionState refresh and explicit target-selection policy;
6. request-idempotency/concurrent decision hardening;
7. shared-family recommendation/decision API and UI boundaries;
8. provider connectors/live freshness, basket/order lifecycle, then learned ranking.

## Resume procedure

1. read this file and ADR-007;
2. inspect current `main`, active branch and compare state;
3. inspect migration heads/current state;
4. inspect relevant app validation commands and CI workflows;
5. confirm whether the exact current branch head has explicit local green validation;
6. do not PR/merge an unvalidated head;
7. after merge, verify new exact `main` before creating the next branch.
