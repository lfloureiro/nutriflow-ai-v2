# Domain implementation status

This is the compact current-status map for NutriFlow AI v2. Detailed semantics live in the linked domain/UX documents and ADRs. `docs/development-continuity.md` is the handover entry point.

## Stable integrated baseline

Integrated capabilities include:

- Family/Person core model, profile and anthropometric history;
- goals, mandatory/advisory NutritionConstraint, FoodPreference and adverse-reaction safety;
- recurring/one-off ScheduleEntry practical context;
- versioned NutritionTarget, DailyHealthState and DailyNutritionState;
- Family MealEvent with Person-specific MealParticipant and Serving records;
- FoodItem/Recipe catalogue with versioned composition snapshots and nutrient components;
- deterministic Serving nutrition calculation with safe unit conversion and exact provenance;
- deterministic hard-rule-first meal recommendation, including fail-closed missing mandatory nutrient data;
- persisted recommendation runs/options, append-only feedback and accepted/modified materialization;
- deterministic DailyNutritionState recalculation from authoritative Serving history;
- shared-family recommendation/materialization with Person-specific portions and fairness-first ranking;
- persisted home/pantry/restaurant/delivery/store practical availability;
- quantity-aware pantry stock and transient shopping requirements;
- commercial opening windows and provider offer metadata;
- person recommendation API, practical orchestration API and recommendation decision API;
- planning-bootstrap API for server-authoritative current state/composition discovery;
- explicit development demo dataset for local end-to-end testing;
- Family dashboard read model for current-day Family member evidence and meal agenda;
- Family-first progressive-disclosure frontend architecture (ADR-034);
- visible responsive application shell with `Início`, `Refeições`, `Pessoas`, `Casa`, `Mais`;
- lightweight Family Home backed by the server dashboard read model.

Integrated baseline after PR #30:

```text
main SHA:      e5c52531dcc7397592643ea712bf9b1d90e00bbd
schema head:   a7c4e9f2b6d1
API tests:     106
Web tests:     14
```

## Current feature branch: representative Family Home demo data

Branch:

```text
feature/demo-family-dashboard-data
```

Merge base:

```text
e5c52531dcc7397592643ea712bf9b1d90e00bbd
```

No database migration and no production-domain behavior change.

Implemented on the branch:

- expands the explicit development-only `NutriFlow Demo` Family from one to four synthetic members;
- keeps `Pessoa Demo` as the fixed primary recommendation/planning Person;
- adds `Marta Demo`, `Rui Demo` and `Inês Demo` with deterministic reserved IDs;
- adds varied current-day DailyHealthState data for all four members;
- adds current-day DailyNutritionState summaries for three members;
- deliberately leaves selected health/nutrition fields absent to exercise Home missing-data states;
- adds deterministic completed breakfast, planned lunch and planned shared dinner MealEvents;
- adds deterministic MealParticipants for two-person and four-person agenda rows;
- keeps the six versioned meal candidates and the primary preference/sodium hard-exclusion fixture unchanged;
- preserves the original primary DailyNutritionState identity so previously seeded local databases can be refreshed without unique-key conflicts;
- keeps all data synthetic, explicit, idempotent, isolated and never auto-seeded;
- adds API coverage proving dashboard variation, agenda participants and repeated-seed idempotency.

Authoritative docs:

- `docs/domain/development-demo-dataset.md`;
- `docs/decisions/ADR-033-development-demo-data-is-explicit-idempotent-and-isolated.md`;
- `docs/ux/family-home-shell.md`.

Expected validation baseline:

```text
API: Alembic metadata clean, Ruff clean, 107 pytest tests
Web: 14 Vitest tests, strict TypeScript check, production Vite build
```

## Family Home UX boundary

Home answers:

> Como está a família hoje?

It intentionally does not become a dense health dashboard. It shows a maximum of four compact indicators per Person and the current meal agenda. No aggregate Family health score is produced.

The enriched demo exists to exercise this exact visual boundary: values differ across members and selected evidence is deliberately absent. Missing current-day health/nutrition state remains unavailable; the browser does not fall back to a previous day or infer clinical meaning.

## Meals UX boundary

`Refeições` owns the recommendation flow. The current slice still starts with recommendation planning rather than the future `Hoje`/`Semana` meal map.

The browser remains subordinate to backend semantics:

- DailyNutritionState is selected by planning bootstrap;
- Food/Recipe composition version is selected by the server;
- hard constraints and safety run before ranking;
- commercial availability cannot override nutrition safety;
- accepted options materialize through the recommendation-decision API.

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
- Family dashboard exposes persisted evidence without medical interpretation;
- missing dashboard evidence remains `null` rather than zero or previous-day fallback;
- web does not select state/composition versions independently or reproduce safety/ranking rules;
- ineligible options cannot be materialized and rejected decisions cannot create meal state;
- DailyNutritionState remains derived from authoritative meal history outside explicit synthetic development fixtures;
- shared meals retain Person-specific portions and safety checks;
- commercial price/availability cannot override safety eligibility;
- demo data is explicit, synthetic, isolated and never auto-seeded;
- warnings remain failures rather than being suppressed.

Known limitations:

- recommendation decision request-level/concurrent idempotency is not yet guaranteed;
- missing real DailyNutritionState is not automatically recalculated by bootstrap/dashboard;
- Family selection remains a development context pending authentication/authorization;
- Person detail screens are not yet implemented;
- `Casa` is not yet functional;
- URL/deep-link routing is not yet introduced;
- recommendation wall-time input retains the existing browser-timezone limitation;
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

After this branch is locally green, PR-tested, visually checked and merged:

1. implement Person overview and secondary navigation;
2. implement Family Meals `Hoje` and `Semana` before the recommendation subflow;
3. add shared-meal drill-down with Person-specific portions;
4. add dedicated Nutrition/Activity/Health/History screens;
5. add profile/goals/constraints/preferences screens;
6. add pantry/shopping UI and durable shopping-list lifecycle;
7. add authentication/authorization before real multi-user deployment;
8. add committed npm lockfile and `npm ci` production hardening;
9. continue provider/live freshness, basket/order and later learned-ranking work.

Every increment follows ADR-007: focused branch, relevant code/tests/docs together, local validation with zero warnings, PR only after local green, CI on the exact head SHA, guarded squash merge, verify new `main`, then start the next branch.
