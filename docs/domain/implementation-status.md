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
- bootstrap-backed web planning with named candidate selection and no DailyNutritionState/composition UUID entry;
- explicit development demo dataset for end-to-end local testing.

Integrated baseline after PR #28:

```text
main SHA:      6d232fd6217fca7853ddefce0273f832ce7488cc
schema head:   a7c4e9f2b6d1
API tests:     103
Web tests:     10
```

## Current feature branch: family-first frontend architecture

Branch:

```text
feature/web-family-home-architecture
```

Merge base:

```text
6d232fd6217fca7853ddefce0273f832ce7488cc
```

No database migration.

Implemented on the branch:

- product-level frontend information architecture centered on a lightweight Family Home;
- explicit progressive-disclosure rule: more focused screens instead of dense all-in-one dashboards;
- primary navigation decision: Início, Refeições, Pessoas, Casa and Mais;
- Person drill-down structure for overview, nutrition, activity, health, history and profile;
- Meals kept as a parallel family workflow rather than becoming the Home;
- chart-density rules that keep Home and Person overview lightweight;
- `GET /api/families/{family_id}/dashboard?on_date=YYYY-MM-DD` compact Family Home read model;
- server-side Family-local-day resolution when `on_date` is omitted;
- latest exact-day DailyHealthState and DailyNutritionState per Family member;
- explicit `null` for missing member evidence rather than zero/fallback inference;
- current-day planned/prepared/served/completed MealEvents with participant Person IDs;
- cancelled/replaced meals omitted from the normal Home agenda;
- typed web FamilyDashboard contracts and API client path/function;
- API tests for latest-state selection, Family-timezone meal boundaries, missing evidence and unknown Family;
- Web unit coverage for dashboard URL construction.

Authoritative docs:

- `docs/ux/frontend-information-architecture.md`;
- `docs/domain/family-dashboard-read-model.md`;
- `docs/decisions/ADR-034-family-first-progressive-disclosure-web-navigation.md`.

Expected validation baseline:

```text
API: Alembic metadata clean, Ruff clean, 106 pytest tests
Web: 11 Vitest tests, strict TypeScript check, production Vite build
```

## Family Home read-model semantics

Endpoint:

```text
GET /api/families/{family_id}/dashboard?on_date=YYYY-MM-DD
```

The endpoint is intentionally a read model for presentation. It does not recalculate derived states, infer medical meaning or create a combined family health score.

For every Family member it returns the latest persisted health/nutrition state for the exact dashboard date when available. Missing current-day state remains `null`.

Meal inclusion is based on the persisted Family timezone, not UTC calendar boundaries. Normal Home agenda statuses are planned, prepared, served and completed.

## Frontend direction

Primary navigation:

```text
Início      family overview today
Refeições   today/week/recommendation/shared-meal detail
Pessoas     Person overview and individual drill-down
Casa        pantry and later shopping
Mais        settings, integrations and administration
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

UI density rules:

- one screen should answer one primary question;
- Family Home should be compact member cards plus today's meals;
- Home normally has zero or one small chart;
- Person overview normally has at most one primary chart;
- detailed analytics live on dedicated screens;
- missing evidence renders as unavailable/unknown, never zero;
- no aggregate health score is invented without a future explicit domain definition.

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
- practical source alternatives keep any-source semantics and unknown remains distinct from unavailable;
- ineligible options cannot be materialized and rejected decisions cannot create meal state;
- DailyNutritionState remains derived from authoritative meal history outside explicit synthetic development fixtures;
- shared meals retain person-specific portions and safety checks;
- commercial price/availability cannot override safety eligibility;
- demo data is explicit, isolated and never auto-seeded;
- warnings remain failures rather than being suppressed.

Known limitations:

- recommendation decision request-level/concurrent idempotency is not yet guaranteed;
- missing real DailyNutritionState is not automatically recalculated by bootstrap/dashboard;
- Family selection remains a development UUID entrypoint pending authentication/authorization;
- committed npm lockfile / `npm ci` hardening is still pending;
- the existing recommendation screen has not yet been moved into the new application shell.

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

After this branch is locally green, PR-tested and merged:

1. implement the responsive application shell and primary navigation;
2. implement the Family Home visually against the new dashboard endpoint;
3. enrich demo data with representative health/activity and additional members when useful for UI validation;
4. implement Person overview and drill-down navigation;
5. move recommendation into Refeições and add today/week family meal views;
6. add shared-meal drill-down with Person-specific portions;
7. add dedicated Nutrition/Activity/Health/History screens;
8. add profile/goals/constraints/preferences screens;
9. add authentication/authorization before real multi-user deployment;
10. continue pantry/shopping/provider and later learned-ranking work.

Every increment follows ADR-007: focused branch, relevant code/tests/docs together, local validation with zero warnings, PR only after local green, CI on the exact head SHA, guarded squash merge, verify new `main`, then start the next branch.
