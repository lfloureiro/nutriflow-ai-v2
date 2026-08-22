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
- Person recommendation API, practical orchestration API and recommendation decision API;
- planning-bootstrap API for server-authoritative current state/composition discovery;
- explicit development demo dataset for local end-to-end testing;
- Family dashboard read model for current-day Family member evidence and meal agenda;
- Family-first progressive-disclosure frontend architecture (ADR-034);
- visible responsive application shell with `Início`, `Refeições`, `Pessoas`, `Casa`, `Mais`;
- lightweight Family Home backed by the server dashboard read model;
- representative four-member synthetic demo data for Family-level UI validation.

Integrated baseline after PR #31:

```text
main SHA:      e95270a4372aa767bded205cdb9f536480cecc27
schema head:   a7c4e9f2b6d1
API tests:     107
Web tests:     14
```

## Current feature branch: Person overview

Branch:

```text
feature/web-person-overview
```

Merge base:

```text
e95270a4372aa767bded205cdb9f536480cecc27
```

No database migration and no backend-domain behavior change.

Implemented on the branch:

- first real Person drill-down from a Family Home member card;
- direct `Pessoas` navigation opens the member list, while a Family Home card opens that Person directly;
- explicit Person back-navigation to the member list;
- secondary Person navigation: `Visão geral`, `Nutrição`, `Atividade`, `Saúde`, `Histórico`, `Perfil`;
- implemented `Visão geral` with a deliberately small current-day metric set;
- energy consumed and remaining range from persisted DailyNutritionState;
- steps and active energy from persisted DailyHealthState;
- latest weight and persisted 7-day trend;
- sleep duration and resting heart rate;
- current-day Person meal list filtered from Family dashboard `participant_person_ids`;
- explicit missing-data presentation rather than zero or previous-day fallback;
- dedicated section placeholders for later focused screens instead of overloading the overview;
- no chart yet because the current read model does not provide a historical time series;
- no medical interpretation, synthetic health score, browser-authored targets or client-side safety logic;
- responsive Person layout with compact horizontal secondary navigation and mobile single-column metrics;
- Web unit coverage for Person meal filtering.

Authoritative docs:

- `docs/ux/person-overview.md`;
- `docs/ux/frontend-information-architecture.md`;
- `docs/ux/family-home-shell.md`;
- `docs/decisions/ADR-034-family-first-progressive-disclosure-web-navigation.md`.

Expected validation baseline:

```text
API: Alembic metadata clean, Ruff clean, 107 pytest tests
Web: 16 Vitest tests, strict TypeScript check, production Vite build
```

## Person overview UX boundary

The Person overview answers:

> Como está esta pessoa hoje?

It is a presentation of current persisted evidence, not an analytical or clinical dashboard. It intentionally contains a small metric set and current-day meal participation.

The overview does not add a chart yet because there is no authoritative time series in the current Family dashboard response. A future Person read model can provide a single primary trend visualization while detailed analytics remain in dedicated sections.

Secondary destinations are visible now to establish the navigation structure, but they remain placeholders until their data/read-model requirements are implemented in focused branches.

## Family Home UX boundary

Home continues to answer:

> Como está a família hoje?

It remains a lightweight Family orientation screen rather than a comprehensive analytics page. Person detail is reached through drill-down.

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
- Person overview presents that evidence without inventing cross-domain meaning;
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
- Person detailed section read models are not yet implemented;
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

1. implement Family Meals `Hoje` and `Semana` before the recommendation subflow;
2. add shared-meal drill-down with Person-specific portions;
3. add dedicated Person Nutrition/Activity/Health/History read models/screens;
4. add Person profile/goals/constraints/preferences screens;
5. add pantry/shopping UI and durable shopping-list lifecycle;
6. add authentication/authorization before real multi-user deployment;
7. add committed npm lockfile and `npm ci` production hardening;
8. continue provider/live freshness, basket/order and later learned-ranking work.

Every increment follows ADR-007: focused branch, relevant code/tests/docs together, local validation with zero warnings, PR only after local green, CI on the exact head SHA, guarded squash merge, verify new `main`, then start the next branch.
