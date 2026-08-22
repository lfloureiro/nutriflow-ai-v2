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

PR #27 wired the web UI to server-authoritative planning bootstrap evidence and was locally green, API/Web CI-green on the exact head, and squash-merged.

Exact integrated baseline:

```text
main SHA:        415e56823ae817972162fdc63d39722f58055658
schema head:     a7c4e9f2b6d1
API tests:       100
Web tests:       10
```

Integrated web planning flow:

```text
Family ID -> Person
GET  /api/persons/{person_id}/planning-bootstrap?scheduled_at=...
named Food/Recipe candidate selection
POST /api/persons/{person_id}/meal-recommendations/practical
POST /api/recommendation-options/{option_id}/decision
```

DailyNutritionState and composition snapshot UUIDs are no longer user inputs. The browser keeps persisted composition IDs internal and remains subordinate to backend eligibility/ranking/safety semantics.

Detailed semantics: `docs/ux/web-bootstrap-selection-flow.md`, ADR-032.

## Current feature branch

```text
feature/demo-development-dataset
```

Merge base:

```text
415e56823ae817972162fdc63d39722f58055658
```

Schema head remains:

```text
a7c4e9f2b6d1
```

No migration. Production startup is unchanged and never auto-seeds.

Current scope:

- add `python -m app.demo_seed` as an explicit local-development command;
- create one fixed `NutriFlow Demo` Family and `Pessoa Demo` Person;
- create a synthetic current-Europe/Lisbon-date DailyNutritionState;
- create six Family-scoped demo FoodItems with versioned energy/protein/fiber/sodium composition evidence;
- add a synthetic pasta preference for ranking explanation;
- add a synthetic mandatory sodium maximum so the pizza demonstrates a hard exclusion;
- keep `demo:` catalogue keys and `source="demo"` provenance explicit;
- make repeated execution idempotent for the same date/catalogue version;
- never delete or rewrite unrelated Family data;
- raise on reserved demo catalogue-key ownership conflict;
- print Family/Person/state/date/candidate information after committing;
- document that the data is synthetic development data, not production or medical guidance.

Expected validation baseline:

```text
API: Alembic metadata clean, Ruff clean, 103 pytest tests
Web: unchanged integrated 10 Vitest tests
```

Authoritative current-branch docs:

- `docs/domain/development-demo-dataset.md`;
- `docs/decisions/ADR-033-development-demo-data-is-explicit-idempotent-and-isolated.md`;
- `docs/domain/implementation-status.md`;
- `apps/web/README.md`.

Do not open a PR until the exact current branch head receives explicit local green confirmation for the API gates. Web code is unchanged, so the existing 10-test web baseline remains integrated.

## Demo execution

After pulling the current feature branch and completing local validation, a developer may populate the local database with:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\api
python -m app.demo_seed
```

The command prints the Family ID currently needed by the pre-authentication UI. On a fresh database the expected fixed ID is:

```text
11111111-1111-4111-8111-111111111111
```

The seed is allowed only as an explicit development action. It is not a substitute for authentication/authorization and must not be wired into API/web startup.

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
- DailyNutritionState remains derived from authoritative meal history outside explicit synthetic development fixtures;
- shared meals keep person-specific portions/safety checks;
- demo data remains explicit, isolated, identifiable and never auto-seeded;
- warnings remain failures rather than suppressions.

Known limitations:

- Family UUID remains a development entrypoint because authentication/authorization is not implemented;
- bootstrap does not create a missing real DailyNutritionState;
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

After the demo branch is locally green, PR-tested and merged:

1. seed the local development database and run the complete browser flow end-to-end, fixing any integration/usability defect exposed by real use;
2. add authentication and explicit Family/Person authorization context;
3. commit an npm lockfile and switch Web CI to `npm ci` before production;
4. add profile/goals/constraints/preferences and daily plan/history web slices;
5. add pantry/shopping UI plus durable shopping-list lifecycle when needed;
6. add background/event-driven DailyNutritionState refresh and explicit target-selection policy;
7. harden recommendation-decision request idempotency/concurrency;
8. expose shared-family recommendation/decision API and UI boundaries;
9. add provider connectors/live freshness, basket/order lifecycle, then learned ranking.

## Resume procedure

1. read this file and ADR-007;
2. inspect current `main`, active branch and compare state;
3. inspect migration heads/current state;
4. inspect relevant app validation commands and CI workflows;
5. confirm whether the exact current branch head has explicit local green validation;
6. do not PR/merge an unvalidated head;
7. after merge, verify new exact `main` before creating the next branch.
