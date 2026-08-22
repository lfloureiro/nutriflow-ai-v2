# Domain implementation status

This is the compact current-status map for NutriFlow AI v2. Detailed semantics live in the linked domain documents and ADRs. `docs/development-continuity.md` is the handover entry point for resuming development.

## Stable integrated baseline

The following capabilities are integrated in `main`.

### Core person/family model

- Family aggregate root and Person membership;
- locale/timezone support;
- PersonProfile and anthropometric history;
- initial Family/Person API routes and services.

### Goals, constraints, preferences and reactions

- NutritionGoal history;
- NutritionConstraint minimum/maximum/exclusion semantics;
- mandatory versus advisory rules with provenance and validity;
- FoodPreference likes/dislikes;
- FoodAdverseReaction allergy/intolerance safety semantics.

Preferences are ranking signals. Mandatory constraints and reactions are eligibility rules.

### Schedule and practical time context

- recurring and one-off ScheduleEntry records;
- availability effects, location, flexibility and provenance;
- deterministic DAILY/WEEKLY recurrence evaluation with BYDAY and INTERVAL=1;
- one-off non-neutral entries override recurring entries;
- unsupported recurrence semantics fail explicitly.

Detailed semantics: `docs/domain/schedule-model.md`, ADR-019.

### Nutrition targets and daily state

- versioned NutritionTarget snapshots per Person;
- optional NutritionGoal relation, BMR/TDEE methods, energy range and nutrient components;
- versioned DailyHealthState and DailyNutritionState;
- deterministic DailyNutritionState recalculation from authoritative meal/Serving history;
- local-day timezone boundaries;
- consumed/served/planned precedence without double counting;
- target-aware remaining values and safe nutrient conversion;
- versioned recomputation semantics.

Detailed semantics: `docs/domain/nutrition-target-model.md`, `docs/domain/daily-state-model.md`, `docs/domain/daily-nutrition-recalculation.md`, ADR-008, ADR-011 and ADR-018.

### Health integrations foundation

- Person-scoped HealthConnection records;
- provider lifecycle, permissions and sync metadata;
- normalized HealthMeasurement point/interval records;
- source-chain provenance and deterministic deduplication;
- historical measurement preservation.

Detailed semantics: `docs/domain/health-connection-model.md`, `docs/domain/health-measurement-model.md`, ADR-009 and ADR-010.

### Meals, servings and write safety

- Family-scoped MealEvent;
- one shared MealEvent with multiple MealParticipant records;
- person-specific Serving records;
- planned/served/consumed quantities, energy and nutrients;
- partial-consumption and replacement history;
- Family-scoped MealEvent idempotency key;
- idempotent create semantics;
- immutable planned-meal replacement preserving the old event as `replaced`;
- retry-safe replacement without copying realized values.

There is intentionally no separate SharedMeal table.

Detailed semantics: `docs/domain/meal-model.md`, `docs/domain/meal-replacement-idempotency.md`, ADR-012 and ADR-022.

### Food and recipe catalogue

- FoodItem identity for ingredients/products/dishes/beverages/supplements/generic foods;
- global or Family-specific catalogue objects;
- versioned FoodCompositionSnapshot and nutrient components;
- Recipe, RecipeIngredient and versioned RecipeCompositionSnapshot;
- historical Serving values insulated from later catalogue corrections.

Detailed semantics: `docs/domain/food-catalog-model.md`, ADR-013.

### Serving nutrition calculation

- explicit calculation from selected versioned Food/Recipe composition;
- Decimal arithmetic and persisted precision;
- safe mass (`mg`, `g`, `kg`) and volume (`ml`, `l`) conversion;
- no inferred density or unsafe cross-dimension conversion;
- exact composition provenance;
- shared scaling logic for recommendation candidates.

Detailed semantics: `docs/domain/serving-nutrition-calculation.md`, ADR-014.

### Deterministic recommendation engine

- person-scoped FoodItem/Recipe candidate ranking;
- composition-derived candidate nutrition;
- Recipe ingredient subject expansion;
- active-date preferences/reactions/constraints;
- mandatory adverse-reaction and food/ingredient/recipe exclusion;
- mandatory nutrient maximum checks against consumed + planned + candidate values;
- missing candidate nutrient data under a mandatory maximum fails closed as `mandatory_nutrient_data_missing:<nutrient_key>`;
- explicit zero remains valid nutrient evidence;
- unsupported mandatory semantics and unsafe required conversions fail closed;
- explainable energy, nutrient, preference and advisory-reaction scoring;
- deterministic ordering and engine versioning;
- learned ranking excluded from eligibility.

Detailed semantics: `docs/domain/adaptive-meal-recommendation.md`, ADR-015 and ADR-026.

### Recommendation history, feedback and materialization

- MealRecommendationRun and persisted MealRecommendationOption evidence;
- eligible and excluded candidates preserved with score/explanations/nutrition;
- append-only accepted/rejected/modified feedback;
- accepted/modified recommendations materialized into normal planned MealEvent/MealParticipant/Serving records;
- exact recommendation composition reused for planned Serving nutrition.

Detailed semantics: `docs/domain/recommendation-feedback-model.md`, `docs/domain/recommendation-to-meal-plan.md`, ADR-016 and ADR-017.

### Person recommendation API

Integrated by PR #22.

- `POST /api/persons/{person_id}/meal-recommendations`;
- explicit persisted DailyNutritionState selection;
- planning date/state-date equality;
- explicit FoodCompositionSnapshot/RecipeCompositionSnapshot IDs;
- positive quantity and explicit candidate unit;
- source evidence reloaded from persistence;
- Person/state ownership and Family isolation;
- inactive candidate and duplicate catalogue-key rejection;
- unsafe quantity scaling mapped to semantic API validation;
- existing hard-rule-first recommendation engine reused unchanged;
- one persisted MealRecommendationRun plus every eligible/excluded MealRecommendationOption;
- response includes persisted IDs, ranks, scores, exclusions, explanations and calculated nutrition.

Detailed semantics: `docs/domain/planning-api-vertical-slice.md`, ADR-027.

### Recommendation decision API

Integrated by PR #23.

- `POST /api/recommendation-options/{option_id}/decision`;
- accepted/rejected/modified decisions over persisted recommendation evidence;
- accepted/modified create normal planned MealEvent/MealParticipant/Serving records;
- accepted preserves the recommendation quantity/unit;
- modified can change quantity/unit and recalculates Serving nutrition from the exact persisted composition snapshot;
- rejected creates feedback only and cannot create meal state;
- ineligible options cannot be materialized;
- semantic/domain failures map to 422 and missing options to 404;
- request-level duplicate/concurrent decision idempotency is not yet guaranteed.

Detailed semantics: `docs/domain/recommendation-decision-api.md`, ADR-028.

### Practical recommendation orchestration API

Integrated by PR #24.

- `POST /api/persons/{person_id}/meal-recommendations/practical`;
- explicit persisted DailyNutritionState and composition-snapshot evidence boundary remains mandatory;
- timezone-aware `scheduled_at` must resolve to `planning_date` in the selected DailyNutritionState timezone;
- persisted Person schedule entries are loaded automatically;
- request context supports location, available minutes and kitchen availability;
- practical source kinds are `home`, `pantry`, `restaurant`, `delivery`, `store`;
- default practical sources are home, pantry, restaurant and delivery;
- requested source channels use any-source semantics;
- explicit candidate unavailability occurs only when every requested channel is explicitly unavailable;
- missing source evidence remains unknown rather than being converted into a false exclusion;
- pantry combines quantity-aware stock sufficiency with optional persisted pantry-source metadata;
- commercial sources evaluate opening windows at the requested instant and return active provider offers;
- practical/commercial evidence cannot override hard allergy or mandatory nutrition rules;
- run/options persist through the existing recommendation evidence model;
- request context and active commercial offer keys are recorded for audit.

Detailed semantics: `docs/domain/practical-recommendation-orchestration-api.md`, ADR-029.

### First responsive web recommendation vertical slice

Integrated by PR #25.

- React + TypeScript + Vite application under `apps/web`;
- strict TypeScript configuration and production build;
- typed API contracts/client isolated from presentation code;
- local Vite `/api` proxy to FastAPI;
- Family UUID -> persisted Person selection through the existing API;
- practical meal context form for schedule, location, available minutes, kitchen and source kinds;
- real practical recommendation generation and persisted option display;
- eligible/excluded explanations, compact nutrition and active commercial offers;
- accept/reject actions through the recommendation decision endpoint;
- accepted decisions surface resulting planned-meal materialization;
- Portuguese (`pt-PT`) and English authored UI strings through an i18n boundary;
- Light, Dark and System appearance modes;
- responsive desktop/tablet/mobile layout and keyboard-focus/accessibility baseline;
- seven Vitest unit tests;
- separate Web CI with pinned npm 11.12.1, web tests, strict type-check and production build.

The integrated UI still exposes explicit DailyNutritionState and composition UUIDs pending the bootstrap/discovery wiring increment.

Integrated baseline after PR #25:

```text
main SHA:      a18b61f0d6512c3a91f99d8f34e2e2c3e3fb2808
schema head:   a7c4e9f2b6d1
API tests:     94
Web tests:     7
```

Detailed semantics: `docs/ux/web-recommendation-vertical-slice.md`, ADR-030.

### Shared-family planning

- one common candidate evaluated for multiple Persons;
- person-specific quantities and units;
- per-Person DailyNutritionState, reactions, constraints, preferences and practical checks;
- any participant hard exclusion makes the shared candidate ineligible;
- fairness-first ranking by worst participant, then family average, then deterministic key;
- accepted shared recommendation materialized into one MealEvent with person-specific Servings.

Detailed semantics: `docs/domain/shared-family-meal-optimization.md`, `docs/domain/shared-family-meal-materialization.md`, ADR-020 and ADR-021.

### Persisted practical availability

- Family-scoped MealCandidateAvailability for FoodItem/Recipe sources;
- source kinds `home`, `pantry`, `restaurant`, `delivery`, `store`;
- stable source key, location, lead time, kitchen requirement and explicit availability;
- deterministic aggregation into CandidatePracticalProfile;
- cross-Family protection.

Detailed semantics: `docs/domain/persisted-practical-availability.md`, ADR-023.

### Pantry stock and shopping requirements

Integrated by PR #19.

- Family-scoped PantryStockLot inventory;
- quantity/unit, storage location, expiry, observation time and availability;
- expired/unavailable lot exclusion;
- safe compatible-unit aggregation;
- FoodItem required/available/missing assessment;
- duplicate RecipeIngredient aggregation;
- Recipe pantry sufficiency and recipe-yield scaling;
- exact transient ShoppingRequirement values;
- pantry-derived practical availability.

Detailed semantics: `docs/domain/pantry-stock-shopping-requirements.md`, ADR-024.

### Restaurant/delivery commercial context

Integrated by PR #20.

- MealSourceOpeningWindow linked to MealCandidateAvailability;
- weekly local opening windows with explicit timezone;
- same-day, overnight and full-day semantics;
- absent opening windows mean unknown hours, not closed;
- MealCommercialOffer linked to a concrete practical source;
- Family-scoped offer identity and provider metadata;
- item price/currency, optional delivery fee and minimum order;
- absolute offer validity and provider observation time;
- deterministic commercial planning context;
- practical profiles from usable restaurant/delivery/store sources;
- active offers returned separately from nutrition eligibility;
- no FX inference and no price-based safety override.

Detailed semantics: `docs/domain/restaurant-delivery-commercial-context.md`, ADR-025.

## Current feature branch: web planning bootstrap API

Branch:

```text
feature/web-planning-bootstrap-api
```

Merge base / current integrated `main`:

```text
a18b61f0d6512c3a91f99d8f34e2e2c3e3fb2808
```

Schema head remains:

```text
a7c4e9f2b6d1
```

This branch has no database migration and does not change recommendation eligibility/ranking semantics.

Implemented on the branch:

- `GET /api/persons/{person_id}/planning-bootstrap?scheduled_at=...`;
- timezone-aware scheduled instant required;
- planning date derived in the persisted Person timezone;
- latest persisted DailyNutritionState selected deterministically for that local date;
- missing DailyNutritionState is returned explicitly as `null`, not invented in the browser;
- active global and same-Family FoodItem/Recipe catalogue objects are discoverable;
- another Family's catalogue objects and inactive objects are excluded;
- one latest Food composition with `effective_at <= scheduled_at` per FoodItem;
- one latest Recipe composition with `computed_at <= scheduled_at` per Recipe;
- future composition evidence is never returned as current evidence;
- candidate response includes persisted composition ID plus display/reference metadata required by the web client;
- six API tests cover local-date/latest-state selection, Family isolation, active catalogue scope, Food/Recipe as-of version selection, missing-state semantics and naive-time rejection.

Authoritative branch docs:

- `docs/domain/web-planning-bootstrap-api.md`;
- `docs/decisions/ADR-031-web-planning-bootstrap-discovers-persisted-state-and-composition.md`.

Expected validation baseline:

```text
API: 100 pytest tests, Ruff clean, Alembic metadata clean
Web: unchanged integrated 7 Vitest tests
```

## Safety and correctness invariants

Future work must preserve:

- mandatory adverse reactions and mandatory constraints before ranking;
- learned ranking can reorder eligible candidates only;
- unknown candidate nutrient data cannot satisfy a mandatory nutrient maximum;
- unsupported mandatory semantics and unsafe required conversions fail closed;
- no inferred density;
- exact versioned composition provenance for Serving/recommendation decisions;
- recommendation APIs reference persisted source snapshots rather than client-authored nutrition totals;
- planning bootstrap returns persisted state/composition evidence rather than browser-authored nutrition values;
- planning bootstrap preserves Family isolation and excludes inactive catalogue data;
- future composition evidence cannot be used for an earlier planning instant;
- practical-source alternatives use any-source semantics rather than accidental all-source requirements;
- unknown practical source evidence is distinct from explicit unavailability;
- practical scheduled instants cannot silently use a DailyNutritionState from another local date;
- web presentation does not reproduce or override recommendation eligibility/safety logic;
- ineligible persisted options cannot be materialized;
- rejected decisions cannot create meal state;
- DailyNutritionState remains derived from authoritative meal history;
- Family-scoped data cannot leak across Families;
- shared meals retain person-specific portions and safety checks;
- retries/replacements remain idempotent where the domain explicitly supports them;
- commercial availability/price cannot make a safety-ineligible candidate eligible;
- warnings are treated as test failures rather than suppressed casually.

Current decision API limitation: request-level idempotency and concurrent duplicate suppression are not implemented. Do not infer retry safety from MealEvent idempotency infrastructure elsewhere in the domain.

A separate future policy is still required when the requested planning date has no current DailyNutritionState or when target selection/recalculation must occur automatically. Bootstrap intentionally returns missing state rather than silently creating derived nutrition evidence.

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

Earlier revisions remain authoritative in `database/migrations/versions/`.

## Next planned increments

After the current bootstrap API branch is locally green, PR-tested and merged:

1. wire the web UI to planning bootstrap so users no longer paste DailyNutritionState/composition UUIDs and can choose normal named candidates;
2. add authentication plus explicit Family/Person authorization context before real multi-user deployment;
3. commit an npm lockfile and switch Web CI to `npm ci` before production deployment;
4. expand the web app into profile/goals/constraints/preferences, daily plan/history and pantry/shopping vertical slices;
5. persist shopping-list lifecycle when UI workflows require durable shopping state;
6. add background/event-driven DailyNutritionState refresh and explicit target-selection policy;
7. harden transaction-level request idempotency/concurrent decision races;
8. expose shared-family recommendation/decision API and UI boundaries;
9. add provider connectors/live freshness and basket/order lifecycle;
10. add learned ranking from feedback only after deterministic safety/practical/nutrition layers remain authoritative.

Every increment follows ADR-007: focused branch, relevant code/tests/docs together, local validation with zero warnings, PR only after local green, CI on the exact PR head SHA, guarded squash merge, verify resulting `main`, then start the next branch.
