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
- representative four-member synthetic demo data for Family-level UI validation;
- first lightweight Person overview drill-down with focused secondary navigation.

Integrated baseline after PR #32:

```text
main SHA:      715ce09bc2034d6f88165f288b2d79321bdd4599
schema head:   a7c4e9f2b6d1
API tests:     107
Web tests:     16
```

## Current feature branch: Family Meals Hoje/Semana

Branch:

```text
feature/web-family-meals-today-week
```

Merge base:

```text
715ce09bc2034d6f88165f288b2d79321bdd4599
```

No database migration.

Implemented on the branch:

- new Family meal-calendar read model at `GET /api/families/{family_id}/meals`;
- optional Family-local `start_date` and bounded `days` range (1..14, default 7);
- local-midnight range construction in persisted Family timezone, converted to UTC for querying;
- one explicit response day for every requested local calendar date, including empty days;
- normal Family meal-map statuses limited to planned/prepared/served/completed;
- cancelled/replaced events omitted;
- compact persisted MealParticipant Person names and participant status returned with each meal;
- web contracts/client coverage for the Family meal range;
- primary `Refeições` destination now starts at `Hoje` rather than the recommendation form;
- secondary navigation `Hoje`, `Semana`, `Recomendar`;
- `Hoje` chronological Family agenda;
- `Semana` current Monday-to-Sunday Family-local week as seven readable vertical day sections;
- existing recommendation vertical slice retained under `Recomendar` without changing its safety/ranking semantics;
- Family Home `Planear refeição` opens `Recomendar` directly;
- shared meals remain one Family calendar row with participant names; Person-specific portions remain a later drill-down;
- responsive single-column mobile behavior rather than a dense calendar grid.

Authoritative docs:

- `docs/domain/family-meals-read-model.md`;
- `docs/ux/family-meals-today-week.md`;
- `docs/ux/frontend-information-architecture.md`;
- `docs/decisions/ADR-034-family-first-progressive-disclosure-web-navigation.md`.

Expected validation baseline after implementation:

```text
API: Alembic metadata clean, Ruff clean, 110 pytest tests
Web: 19 Vitest tests, strict TypeScript check, production Vite build
```

These counts are not integrated claims until the exact branch head passes local validation and CI.

## Family Meals UX boundary

`Refeições` answers:

> O que está planeado para a família?

The orientation layer is the Family meal map, not the recommendation form. Users see `Hoje` or `Semana` first and enter `Recomendar` only when they want a generated option.

The weekly view intentionally avoids a dense seven-column planner. Empty days are explicit and active meals remain compact rows with time, title, participants, optional location and state.

The meal calendar does not calculate nutrition or surface Serving-level portions. Shared-meal detail is the next dedicated drill-down.

## Person overview UX boundary

The integrated Person overview answers:

> Como está esta pessoa hoje?

It presents current persisted evidence, keeps missing data explicit and avoids medical interpretation or a synthetic health score. Detailed Person sections remain future focused slices.

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
- Family meal range uses Family-local calendar boundaries and persisted participant membership;
- Person overview presents persisted evidence without inventing cross-domain meaning;
- missing dashboard evidence remains `null` rather than zero or previous-day fallback;
- web does not select state/composition versions independently or reproduce safety/ranking rules;
- ineligible options cannot be materialized and rejected decisions cannot create meal state;
- DailyNutritionState remains derived from authoritative meal history outside explicit synthetic development fixtures;
- shared meals retain Person-specific portions and safety checks even when summarized once in Family calendar views;
- commercial price/availability cannot override safety eligibility;
- demo data is explicit, synthetic, isolated and never auto-seeded;
- warnings remain failures rather than being suppressed.

Known limitations:

- recommendation decision request-level/concurrent idempotency is not yet guaranteed;
- missing real DailyNutritionState is not automatically recalculated by bootstrap/dashboard;
- Family selection remains a development context pending authentication/authorization;
- Family meal detail/Serving portions are not yet implemented;
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

1. add shared-meal drill-down with Person-specific portions;
2. add dedicated Person Nutrition/Activity/Health/History read models/screens;
3. add Person profile/goals/constraints/preferences screens;
4. add pantry/shopping UI and durable shopping-list lifecycle;
5. add authentication/authorization before real multi-user deployment;
6. add committed npm lockfile and `npm ci` production hardening;
7. continue provider/live freshness, basket/order and later learned-ranking work.

Every increment follows ADR-007: focused branch, relevant code/tests/docs together, local validation with zero warnings, PR only after local green, CI on the exact head SHA, guarded squash merge, verify new `main`, then start the next branch.
