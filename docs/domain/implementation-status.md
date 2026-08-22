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
- deterministic hard-rule-first recommendation and persisted recommendation/feedback evidence;
- shared-family recommendation/materialization with Person-specific portions;
- persisted practical availability, pantry stock and commercial offer evidence;
- Person/practical recommendation APIs and planning-bootstrap API;
- explicit development demo dataset;
- Family dashboard read model;
- Family-first responsive application shell;
- lightweight Family Home;
- representative four-member synthetic demo data;
- lightweight Person overview with secondary navigation.

Integrated baseline after PR #32:

```text
main SHA:      715ce09bc2034d6f88165f288b2d79321bdd4599
schema head:   a7c4e9f2b6d1
API tests:     107
Web tests:     16
```

## Current branch: Person meal-label presentation fix

```text
fix/web-person-meal-labels
```

Merge base:

```text
715ce09bc2034d6f88165f288b2d79321bdd4599
```

No database migration and no API/backend-domain change.

Implemented on this branch:

- localizes known Person meal type labels for the active locale;
- localizes known MealEvent status labels for the active locale;
- Portuguese examples: `lunch` -> `Almoço`, `planned` -> `Planeada`, `completed` -> `Concluída`;
- English labels are normalized for presentation as well;
- unknown type/status values remain unchanged rather than being guessed;
- unit coverage verifies known and unknown label behavior;
- distinct persisted MealEvents remain distinct rows even when title/time repeat.

Expected validation baseline:

```text
API: Alembic metadata clean, Ruff clean, 107 pytest tests
Web: 18 Vitest tests, strict TypeScript check, production Vite build
```

## Person overview UX boundary

The Person overview answers:

> Como está esta pessoa hoje?

It presents current persisted evidence without becoming a dense analytical/clinical dashboard. Known domain enum values are translated into user-facing labels, but the browser does not alter the underlying domain records.

A screenshot during visual review also showed several separate planned MealEvents at 11:14. They were created by previous recommendation smoke tests and are real persisted rows, not one row rendered repeatedly. Client-side deduplication would hide authoritative state and is therefore not used.

## Family/Meals boundaries

Family Home remains lightweight. `Refeições` continues to own planning/recommendation. Accepted recommendation options can materialize MealEvents, so persistent development data can accumulate during repeated smoke tests.

An explicit development-demo reset/cleanup path is the next focused development-data increment.

## Safety and correctness invariants

Future work must preserve:

- mandatory safety/constraints before ranking;
- missing mandatory evidence fails closed;
- exact versioned composition provenance;
- server authority over state/composition/safety/ranking;
- missing dashboard evidence remains `null` rather than zero;
- Person overview does not infer clinical meaning;
- separate persisted MealEvents are not hidden by presentation deduplication;
- shared meals retain Person-specific portions;
- demo data remains explicit, synthetic and never auto-seeded;
- warnings remain failures.

Known limitations:

- persistent demo databases can accumulate accepted recommendation MealEvents until reset is added;
- recommendation decision request-level/concurrent idempotency is not yet guaranteed;
- missing real DailyNutritionState is not automatically recalculated by bootstrap/dashboard;
- Family selection remains development context pending authentication/authorization;
- detailed Person section read models are not yet implemented;
- `Casa` is not yet functional;
- URL/deep-link routing is not yet introduced;
- recommendation wall-time input retains the browser-timezone limitation;
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

1. explicit development-demo reset/cleanup;
2. Family Meals `Hoje` and `Semana`;
3. shared-meal drill-down with Person-specific portions;
4. dedicated Person Nutrition/Activity/Health/History read models/screens;
5. Person profile/goals/constraints/preferences;
6. pantry/shopping UI;
7. authentication/authorization;
8. npm lockfile / `npm ci` hardening;
9. provider/live freshness, basket/order and later learned ranking.

Every increment follows ADR-007.
