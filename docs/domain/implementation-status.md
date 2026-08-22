# Domain implementation status

This is the compact current-status map for NutriFlow AI v2. Detailed semantics live in the linked domain/UX documents and ADRs. `docs/development-continuity.md` is the handover entry point.

## Stable integrated baseline

Integrated capabilities include:

- Family/Person core model, profile and anthropometric history;
- goals, mandatory/advisory NutritionConstraint, FoodPreference and adverse-reaction safety;
- recurring/one-off ScheduleEntry practical context;
- versioned NutritionTarget, DailyHealthState and DailyNutritionState;
- Family MealEvent with person-specific MealParticipant and Serving records;
- FoodItem/Recipe catalogue with versioned composition snapshots and nutrient components;
- deterministic Serving nutrition calculation with safe unit conversion and exact provenance;
- deterministic hard-rule-first meal recommendation, including fail-closed missing mandatory nutrient data;
- persisted recommendation runs/options, append-only feedback and accepted/modified materialization;
- deterministic DailyNutritionState recalculation from authoritative Serving history;
- shared-family recommendation/materialization with person-specific portions and fairness-first ranking;
- persisted home/pantry/restaurant/delivery/store practical availability;
- quantity-aware pantry stock and transient shopping requirements;
- commercial opening windows and provider offer metadata;
- person recommendation API, practical orchestration API and recommendation decision API;
- planning-bootstrap API for server-authoritative current state/composition discovery;
- responsive React + TypeScript + Vite web foundation with pt-PT/en, Light/Dark/System and Web CI;
- bootstrap-backed web planning with named candidate selection and no DailyNutritionState/composition UUID entry.

Key documents: `docs/domain/adaptive-meal-recommendation.md`, `docs/domain/practical-recommendation-orchestration-api.md`, `docs/domain/recommendation-decision-api.md`, `docs/domain/web-planning-bootstrap-api.md`, `docs/ux/web-bootstrap-selection-flow.md`.

## Integrated bootstrap-backed web selection

Integrated by PR #27.

The web flow now:

- uses Family ID -> Person selection as the temporary pre-authentication entrypoint;
- loads planning bootstrap for the selected Person and scheduled instant;
- selects the current persisted DailyNutritionState server-side;
- shows named Food/Recipe candidates from server-selected current composition snapshots;
- keeps technical composition IDs internal;
- initializes quantity/unit from server reference values while keeping them editable;
- invalidates stale evidence when Person/time changes;
- explicitly blocks recommendation if the daily state or usable catalogue evidence is missing;
- preserves backend authority for eligibility, exclusions, ranking and decision materialization.

Integrated baseline after PR #27:

```text
main SHA:      415e56823ae817972162fdc63d39722f58055658
schema head:   a7c4e9f2b6d1
API tests:     100
Web tests:     10
```

Detailed semantics: `docs/ux/web-bootstrap-selection-flow.md`, ADR-032.

## Current feature branch: development demo dataset

Branch:

```text
feature/demo-development-dataset
```

Merge base:

```text
415e56823ae817972162fdc63d39722f58055658
```

No database migration and no production startup behavior change.

Implemented on the branch:

- explicit `python -m app.demo_seed` local-development command;
- one dedicated fixed `NutriFlow Demo` Family and `Pessoa Demo` Person;
- current Europe/Lisbon-date DailyNutritionState with synthetic energy/protein/fiber/sodium progress;
- six Family-scoped demo FoodItems with versioned composition/nutrient evidence;
- synthetic preference signal for ranking explanation;
- synthetic mandatory sodium maximum so one demo candidate exercises hard exclusion;
- deterministic demo IDs/catalogue keys and source provenance;
- idempotent repeated execution for the same date/version;
- no deletion/rewrite of unrelated Family data;
- explicit catalogue-key conflict failure rather than silent ownership takeover;
- CLI output of Family ID, Person ID, planning date and candidate count;
- tests covering idempotency/isolation, planning-bootstrap visibility and normal recommendation ranking/exclusion.

The demo is synthetic development data only. It is never created automatically by API/web startup and is not production nutrition guidance.

Authoritative branch docs:

- `docs/domain/development-demo-dataset.md`;
- `docs/decisions/ADR-033-development-demo-data-is-explicit-idempotent-and-isolated.md`.

Expected validation baseline:

```text
API: Alembic metadata clean, Ruff clean, 103 pytest tests
Web: unchanged 10 Vitest tests
```

## Safety and correctness invariants

Future work must preserve:

- mandatory adverse reactions and mandatory constraints before ranking;
- learned ranking may reorder eligible candidates only;
- missing candidate nutrient data cannot satisfy a mandatory nutrient maximum;
- unsupported mandatory semantics and unsafe required conversions fail closed;
- no inferred density;
- exact versioned composition provenance;
- recommendation APIs use persisted source evidence, not client-authored nutrition totals;
- planning bootstrap preserves Person/Family isolation and as-of composition semantics;
- web does not select state/composition versions independently or reproduce safety/ranking rules;
- practical source alternatives keep any-source semantics and unknown remains distinct from unavailable;
- ineligible options cannot be materialized and rejected decisions cannot create meal state;
- DailyNutritionState remains derived from authoritative meal history outside explicit synthetic development fixtures;
- shared meals retain person-specific portions and safety checks;
- commercial price/availability cannot override safety eligibility;
- demo data is explicit, isolated and never auto-seeded;
- warnings remain failures rather than being suppressed.

Known limitations:

- recommendation decision request-level/concurrent idempotency is not yet guaranteed;
- missing real DailyNutritionState is not automatically recalculated by bootstrap;
- Family selection remains a development UUID entrypoint pending authentication/authorization;
- committed npm lockfile / `npm ci` hardening is still pending.

## Current migration tail

```text
a7c4e9f2b6d1  commercial source opening windows and offers
f6b3d8e1a5c2  quantity-aware Family pantry stock lots
e5a2c7d9f4b1  Family-scoped meal candidate availability
d4f8a1b2c6e9  MealEvent Family-scoped idempotency
c3e7f9a1b5d2  recommendation run/option/feedback
a2d6e8f1c3b5  Serving composition provenance
f4b8c2d6a1e3  Food/Recipe catalogue composition
e1c5b7a9d2f4  MealEvent/MealParticipant/Serving
d9f2a7          DailyHealthState/DailyNutritionState
```

## Next planned increments

After the demo branch is locally green, PR-tested and merged:

1. run the seeded web flow end-to-end in the browser and fix any integration/usability defects found through real use;
2. add authentication and explicit Family/Person authorization context before real multi-user deployment;
3. commit an npm lockfile and switch Web CI to `npm ci` before production deployment;
4. add user-facing profile/goals/constraints/preferences and daily plan/history vertical slices;
5. add pantry/shopping UI and persist shopping-list lifecycle when required;
6. add background/event-driven DailyNutritionState refresh plus explicit target-selection policy;
7. harden request idempotency/concurrent recommendation-decision races;
8. expose shared-family recommendation/decision API and UI boundaries;
9. add provider connectors/live freshness and basket/order lifecycle;
10. add learned ranking only after deterministic safety/practical/nutrition layers remain authoritative.

Every increment follows ADR-007: focused branch, relevant code/tests/docs together, local validation with zero warnings, PR only after local green, CI on the exact head SHA, guarded squash merge, verify new `main`, then start the next branch.
