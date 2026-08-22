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
- first lightweight Person overview drill-down;
- Family `Refeições > Hoje / Semana / Recomendar` workflow backed by the Family-local calendar read model.

Integrated baseline after PR #33:

```text
main SHA:      e0bdd8a9c8cc40f58ab67f14727ab134ac2156dc
schema head:   a7c4e9f2b6d1
API tests:     110
Web tests:     19
```

## Current feature branch: shared Family meal detail

Branch:

```text
feature/web-family-meal-detail
```

Merge base:

```text
e0bdd8a9c8cc40f58ab67f14727ab134ac2156dc
```

No database migration.

Implemented on the branch:

- `GET /api/families/{family_id}/meals/{meal_event_id}` Family-scoped read-only detail endpoint;
- endpoint query constrained by both Family ID and MealEvent ID;
- persisted MealParticipant Person identity/name/status returned for the selected shared meal;
- persisted Person-specific Serving rows returned with planned/served/consumed quantity and energy lifecycle evidence;
- no Serving recalculation, nutrient aggregation, recommendation ranking or safety inference in the detail read model;
- cross-Family meal lookup returns `404` rather than exposing another Family's meal;
- `Hoje` and `Semana` meal rows are accessible drill-down buttons rather than expanded dense rows;
- selecting a meal opens a separate focused `Refeição` screen;
- detail shows Family-local date/time, location/status, vertical participant cards and each Person's recorded portions;
- concise Serving presentation chooses existing consumed evidence, then served, then planned; this is presentation selection only;
- missing Serving rows stay explicit rather than being inferred or displayed as zero;
- pt-PT/en copy and responsive single-column detail layout;
- explicit demo seed enriched with deterministic/idempotent Person-specific Serving fixtures for all ten demo MealParticipants;
- advanced explanation, alternatives/edit commands, nutrient breakdowns and safety-result UI deliberately remain outside this increment.

Authoritative docs:

- `docs/domain/family-meals-read-model.md`;
- `docs/ux/family-meal-detail.md`;
- `docs/ux/family-meals-today-week.md`;
- `docs/ux/frontend-information-architecture.md`;
- `docs/decisions/ADR-034-family-first-progressive-disclosure-web-navigation.md`.

Expected validation baseline after implementation:

```text
API: Alembic metadata clean, Ruff clean, 112 pytest tests
Web: 21 Vitest tests, strict TypeScript check, production Vite build
```

These counts are expectations only until the exact branch head is locally validated.

## Family Meals UX boundary

`Refeições` first answers:

> O que está planeado para a família?

`Hoje` and `Semana` remain low-density orientation screens. A shared MealEvent appears once and can now be opened into the dedicated `Refeição` screen.

The detail screen answers:

> Qual é a refeição e qual é a porção de cada pessoa?

It preserves the domain structure `MealEvent -> MealParticipant -> Serving` rather than duplicating the shared meal per Person.

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
- Family meal detail exposes persisted Serving evidence without deriving another Person's portion or new nutrition totals;
- Person overview presents persisted evidence without inventing cross-domain meaning;
- missing dashboard/detail evidence remains missing rather than zero or previous-value fallback;
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
- meal-detail explanation/alternatives/edit commands are not yet implemented;
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

1. add dedicated Person Nutrition/Activity/Health/History read models/screens;
2. add Person profile/goals/constraints/preferences screens;
3. add pantry/shopping UI and durable shopping-list lifecycle;
4. add authentication/authorization before real multi-user deployment;
5. add committed npm lockfile and `npm ci` production hardening;
6. continue meal explanation/alternative/edit flows when their command/read semantics are defined;
7. continue provider/live freshness, basket/order and later learned-ranking work.

Every increment follows ADR-007: focused branch, relevant code/tests/docs together, local validation with zero warnings, PR only after local green, CI on the exact head SHA, guarded squash merge, verify new `main`, then start the next branch.
