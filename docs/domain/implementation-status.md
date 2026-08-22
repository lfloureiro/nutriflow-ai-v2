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
- responsive React + TypeScript + Vite web foundation with pt-PT/en, Light/Dark/System and Web CI.

Key documents: `docs/domain/adaptive-meal-recommendation.md`, `docs/domain/practical-recommendation-orchestration-api.md`, `docs/domain/recommendation-decision-api.md`, `docs/ux/web-recommendation-vertical-slice.md`.

## Planning bootstrap API

Integrated by PR #26.

Endpoint:

```text
GET /api/persons/{person_id}/planning-bootstrap?scheduled_at=...
```

It:

- requires a timezone-aware planning instant;
- derives the planning date in the persisted Person timezone;
- selects the latest persisted DailyNutritionState for that local date;
- returns missing daily state explicitly as `null`;
- exposes active global and same-Family FoodItem/Recipe catalogue entries only;
- excludes inactive and cross-Family catalogue data;
- selects the latest non-future Food/Recipe composition valid at the requested instant;
- returns human display metadata plus authoritative composition IDs for recommendation calls.

Integrated baseline after PR #26:

```text
main SHA:      3ae41826a873d428a112c4060c95bea0856ffbbb
schema head:   a7c4e9f2b6d1
API tests:     100
Web tests:     7
```

Detailed semantics: `docs/domain/web-planning-bootstrap-api.md`, ADR-031.

## Current feature branch: bootstrap-backed web selection

Branch:

```text
feature/web-bootstrap-selection-ui
```

Merge base:

```text
3ae41826a873d428a112c4060c95bea0856ffbbb
```

No database migration and no backend recommendation-rule change.

Implemented on the branch:

- typed web contracts/client for planning bootstrap;
- Person + scheduled instant automatically load server-authoritative planning evidence;
- DailyNutritionState UUID is no longer a user input;
- composition snapshot UUIDs are no longer user inputs;
- named Food/Recipe selection shows brand/reference serving/energy metadata;
- selected candidate identity remains the server-returned persisted composition internally;
- candidate quantity/unit initialize from the server reference serving and remain editable;
- duplicate selected composition IDs are disabled in the form;
- changing Person or planning instant invalidates old bootstrap/candidate/recommendation evidence;
- missing DailyNutritionState and empty current catalogue are explicit UI states;
- recommendation submission is disabled when required server evidence is missing;
- recommendation eligibility/ranking remains server-authoritative;
- web tests expand from 7 to 10: bootstrap URL encoding, bootstrap candidate mapping and new i18n state copy.

Authoritative branch docs:

- `docs/ux/web-bootstrap-selection-flow.md`;
- `docs/decisions/ADR-032-web-planning-uses-server-bootstrap-evidence.md`.

Expected validation baseline:

```text
API: Alembic metadata clean, Ruff clean, 100 pytest tests
Web: 10 Vitest tests, strict TypeScript check, production Vite build
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
- DailyNutritionState remains derived from authoritative meal history;
- shared meals retain person-specific portions and safety checks;
- commercial price/availability cannot override safety eligibility;
- warnings remain failures rather than being suppressed.

Known limitations:

- recommendation decision request-level/concurrent idempotency is not yet guaranteed;
- missing DailyNutritionState is not automatically recalculated by bootstrap;
- Family selection remains a development UUID entrypoint pending authentication/authorization.

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

After this web branch is locally green, PR-tested and merged:

1. add authentication and explicit Family/Person authorization context before real multi-user deployment;
2. commit an npm lockfile and switch Web CI to `npm ci` before production deployment;
3. add user-facing profile/goals/constraints/preferences and daily plan/history vertical slices;
4. add pantry/shopping UI and persist shopping-list lifecycle when required;
5. add background/event-driven DailyNutritionState refresh plus explicit target-selection policy;
6. harden request idempotency/concurrent recommendation-decision races;
7. expose shared-family recommendation/decision API and UI boundaries;
8. add provider connectors/live freshness and basket/order lifecycle;
9. add learned ranking only after deterministic safety/practical/nutrition layers remain authoritative.

Every increment follows ADR-007: focused branch, relevant code/tests/docs together, local validation with zero warnings, PR only after local green, CI on the exact head SHA, guarded squash merge, verify new `main`, then start the next branch.
