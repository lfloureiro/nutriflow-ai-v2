# Domain implementation status

This document is the compact current-status map for NutriFlow AI v2. Detailed semantics live in the linked domain documents and ADRs. `docs/development-continuity.md` is the handover entry point for resuming development.

## Stable integrated baseline

The following capabilities are already integrated in `main`.

### Family, Person and profile history

Implemented:

- Family aggregate root and Person membership;
- locale/timezone support;
- PersonProfile;
- historical anthropometric measurements;
- API routes/services for the initial Family/Person vertical slice.

### Goals, constraints, preferences and reactions

Implemented:

- NutritionGoal history;
- NutritionConstraint minimum/maximum/exclusion semantics;
- mandatory versus advisory constraints;
- professional provenance and validity periods;
- FoodPreference likes/dislikes with intensity;
- FoodAdverseReaction allergy/intolerance safety semantics.

Preferences are ranking signals. Adverse reactions and mandatory constraints remain eligibility rules.

### Schedule

Implemented:

- recurring and one-off ScheduleEntry records;
- availability effects;
- recurrence-rule storage;
- timezone-aware local time semantics;
- flexibility, location, provenance and notes;
- deterministic practical evaluation for DAILY/WEEKLY recurrence with BYDAY and INTERVAL=1;
- one-off non-neutral availability effects overriding recurring effects;
- explicit failure for unsupported recurrence semantics.

Detailed semantics: `docs/domain/schedule-model.md`, ADR-019.

### Nutrition targets

Implemented:

- versioned NutritionTarget snapshots per Person;
- optional NutritionGoal relationship;
- BMR/TDEE estimates and methods;
- target energy range;
- extensible nutrient target components;
- calculation version/input provenance and validity periods.

Detailed semantics: `docs/domain/nutrition-target-model.md`, ADR-008.

### Health connections and measurements

Implemented:

- Person-scoped HealthConnection records;
- provider-agnostic lifecycle, permissions and sync metadata;
- secret-free credential references;
- normalized HealthMeasurement point/interval records;
- provider/origin/source-chain provenance;
- deterministic cross-path deduplication;
- historical measurement preservation after connection removal.

Detailed semantics: `docs/domain/health-connection-model.md`, `docs/domain/health-measurement-model.md`, ADR-009 and ADR-010.

### Daily health and nutrition state

Implemented:

- versioned DailyHealthState snapshots per Person/local date;
- weight, activity, energy, sleep and heart-rate/HRV context;
- versioned DailyNutritionState snapshots;
- consumed/planned/remaining energy;
- nutrient-level state components;
- deterministic recalculation from authoritative MealEvent/MealParticipant/Serving history;
- explicit local-day timezone boundaries;
- served/consumed/planned precedence without double counting;
- optional target-aware remaining values;
- safe nutrient unit conversion;
- same-calculation-version recomputation in place and separate algorithm versions.

Daily state is derived/recalculable rather than authoritative source history.

Detailed semantics: `docs/domain/daily-state-model.md`, `docs/domain/daily-nutrition-recalculation.md`, ADR-011 and ADR-018.

### Meals and servings

Implemented:

- Family-scoped MealEvent;
- one shared MealEvent with multiple MealParticipant records;
- person-specific Serving records;
- planned/served/consumed quantities and energy;
- nutrient snapshots per Serving;
- partial-consumption and replacement history;
- Family-scoped MealEvent idempotency key;
- idempotent create semantics;
- immutable planned-meal replacement with old event preserved as `replaced`;
- retry-safe replacement semantics;
- no copying of realized values into replacement plans.

There is intentionally no separate SharedMeal table.

Detailed semantics: `docs/domain/meal-model.md`, `docs/domain/meal-replacement-idempotency.md`, ADR-012 and ADR-022.

### Food and recipe catalogue

Implemented:

- FoodItem identities for ingredients, products, dishes, beverages, supplements and generic foods;
- global or Family-specific catalogue objects;
- versioned FoodCompositionSnapshot and nutrient components;
- Recipe/RecipeIngredient;
- versioned RecipeCompositionSnapshot and nutrient components;
- historical Serving nutrition insulated from later catalogue corrections.

Detailed semantics: `docs/domain/food-catalog-model.md`, ADR-013.

### Serving nutrition calculation

Implemented:

- explicit calculation from a selected versioned Food/Recipe composition snapshot;
- Decimal arithmetic and persisted precision;
- safe mass conversion (`mg`, `g`, `kg`);
- safe volume conversion (`ml`, `l`);
- no inferred density or cross-dimension conversion;
- exact composition provenance on Serving;
- reusable composition scaling for recommendation candidates.

Detailed semantics: `docs/domain/serving-nutrition-calculation.md`, ADR-014.

### Deterministic recommendation engine

Implemented:

- person-scoped FoodItem/Recipe candidate ranking;
- composition-derived candidate nutrition;
- Recipe ingredient subject expansion;
- active-date preferences/reactions/constraints;
- mandatory adverse-reaction exclusion;
- mandatory food/ingredient/recipe exclusions;
- mandatory nutrient-max checks against consumed + already planned + candidate nutrition;
- explicit failure for unsupported mandatory semantics and unsafe required conversion;
- energy-fit, nutrient-deficit, preference and advisory-reaction scoring;
- deterministic ordering, score breakdowns, exclusion reasons and explanations;
- learned ranking excluded from eligibility decisions.

Detailed semantics: `docs/domain/adaptive-meal-recommendation.md`, ADR-015.

### Recommendation history, feedback and meal materialization

Implemented:

- MealRecommendationRun per Person/execution;
- persisted eligible and excluded MealRecommendationOption snapshots;
- engine version, context, subjects, nutrition, rank, score and explanations;
- exact Food/Recipe composition traceability when available;
- append-only accepted/rejected/modified feedback;
- feedback link to resulting Serving;
- accepted/modified eligible recommendations materialized into normal planned meals;
- exact recommendation composition reused for planned Serving nutrition.

Detailed semantics: `docs/domain/recommendation-feedback-model.md`, `docs/domain/recommendation-to-meal-plan.md`, ADR-016 and ADR-017.

### Practical recommendation context

Implemented:

- timezone-aware intended meal instant;
- ScheduleEntry feasibility;
- location filtering;
- preparation-time filtering;
- kitchen-availability filtering;
- explicit candidate availability state;
- unknown practical metadata does not create a false exclusion;
- practical exclusions occur before normal deterministic safety/nutrition ranking.

Detailed semantics: `docs/domain/recommendation-practical-context.md`, ADR-019.

### Shared-family optimization and materialization

Implemented:

- one common FoodItem/Recipe candidate evaluated for multiple Persons;
- person-specific quantity/unit;
- each Person evaluated independently against DailyNutritionState, reactions, constraints, preferences and practical context;
- any participant hard exclusion makes the shared candidate ineligible;
- fairness-first ranking: maximize the worst participant score, then family average, then deterministic key;
- accepted shared recommendation materializes into one MealEvent with one MealParticipant/Serving per Person;
- exact person-specific portions and composition provenance retained.

Detailed semantics: `docs/domain/shared-family-meal-optimization.md`, `docs/domain/shared-family-meal-materialization.md`, ADR-020 and ADR-021.

### Persisted practical availability

Implemented:

- Family-scoped MealCandidateAvailability for FoodItem/Recipe sources;
- source kinds `home`, `pantry`, `restaurant`, `delivery`, `store`;
- stable source key;
- location, preparation/lead time, kitchen requirement and explicit availability;
- provider/source provenance;
- deterministic source-kind filtering and aggregation into CandidatePracticalProfile;
- cross-Family catalogue protection.

Detailed semantics: `docs/domain/persisted-practical-availability.md`, ADR-023.

### Pantry stock and shopping requirements

Integrated by PR #19.

Implemented:

- Family-scoped PantryStockLot operational inventory;
- stable stock keys, positive quantity/unit, storage location, expiry and availability;
- timezone-aware observation and evaluation time;
- expired/unavailable lot exclusion;
- safe compatible-unit aggregation;
- FoodItem required/available/missing quantity assessment;
- duplicate RecipeIngredient aggregation;
- Recipe pantry sufficiency for explicit batch multipliers;
- exact transient ShoppingRequirement values for missing ingredients;
- Recipe candidate scaling from requested candidate amount to Recipe yield;
- pantry-derived CandidatePracticalProfile availability;
- Family isolation and fail-closed unsafe conversions.

Detailed semantics: `docs/domain/pantry-stock-shopping-requirements.md`, ADR-024.

## Current feature branch: restaurant/delivery commercial context

Branch: `feature/restaurant-delivery-commercial-context`.

This branch adds durable volatile commercial state without placing it in FoodItem/Recipe nutrition composition.

Implemented on the branch:

- MealSourceOpeningWindow linked to MealCandidateAvailability;
- weekly local opening windows with explicit timezone;
- same-day, overnight and full-day window semantics;
- optional local-date validity range;
- missing opening windows treated as unknown rather than closed;
- MealCommercialOffer linked to a concrete practical source;
- Family-scoped stable offer key;
- provider identity/name;
- item price and explicit three-character currency;
- optional delivery fee and minimum order;
- absolute offer validity and timezone-aware provider observation time;
- deterministic `build_commercial_planning_context()` service;
- practical profiles generated from currently usable restaurant/delivery/store sources;
- active commercial offer snapshots returned separately from eligibility;
- no FX conversion and no price-aware nutrition ranking;
- open source remains practically available when current price data is unknown;
- Family and source-kind boundaries fail explicitly;
- tests for opening hours, closed sources, overnight windows, unknown hours, offer validity, deterministic multi-currency ordering and Family isolation.

Detailed semantics: `docs/domain/restaurant-delivery-commercial-context.md`, ADR-025.

## Safety and correctness invariants

Future work must preserve all of the following:

- mandatory adverse reactions and mandatory constraints run before ranking;
- learned ranking may reorder eligible candidates only;
- unsafe required unit conversions fail closed;
- no inferred density is used;
- historical Serving/recommendation evidence keeps exact provenance;
- DailyNutritionState is derived from authoritative meal history;
- Family-scoped data cannot leak across Families;
- shared meals keep person-specific portions and safety checks;
- retry/replacement history remains idempotent and immutable;
- warnings are treated as test failures rather than routinely suppressed;
- commercial price/opening data cannot make a nutritionally/safety-ineligible candidate eligible.

Known safety-hardening item: mandatory nutrient maxima currently require an explicit policy for candidates whose composition omits the constrained nutrient. This must be reviewed in a dedicated focused increment before broader API/UI exposure rather than changed incidentally.

## Current database migration chain

Current branch head: `a7c4e9f2b6d1`.

Recent chain:

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

CI must be able to apply the complete chain to an empty PostgreSQL database and `alembic check` must report no model/schema drift.

## Validation checkpoint

Last integrated baseline:

- PR #19 merged;
- `main` SHA `672f32673102da9db1e686c89c1f8a0c61ba222f`;
- schema head `f6b3d8e1a5c2`;
- 64 tests locally and in CI.

Current branch target after its seven new tests:

- schema head `a7c4e9f2b6d1`;
- expected complete API suite: 71 tests;
- PR must not be opened until local Alembic, Ruff and all tests are green with zero warnings.

## Next planned increments

After the current commercial-context branch is locally validated, PR-tested and merged:

1. dedicated fail-closed hardening for mandatory nutrient maxima when candidate nutrient data is missing;
2. API and UI vertical slices over the completed deterministic planning flow;
3. persisted shopping-list lifecycle when UI/API workflows require durable shopping state;
4. background/event-driven DailyNutritionState refresh and explicit target-selection policy;
5. fuller recurrence/calendar override support;
6. persisted family-level recommendation audit history;
7. transaction-level idempotency-race handling at the write API boundary;
8. provider connectors/live commercial freshness policies and basket/order workflows;
9. learned ranking from feedback only after deterministic safety, practical and nutrition layers remain authoritative.

Every increment follows ADR-007: focused branch, code/migration/tests/docs together, local PostgreSQL validation, zero-warning Ruff/pytest, PR only after local green, CI on the exact PR head SHA, guarded squash merge, verify resulting `main`, then start the next branch.
