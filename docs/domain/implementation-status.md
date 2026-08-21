# Domain implementation status

This document tracks the implemented domain baseline so code, migrations, tests and domain documentation evolve together.

## Implemented foundation

### Family and Person

Implemented:

- Family aggregate root;
- Person linked to Family;
- locale and timezone support;
- API routes and services for Family and Person;
- persistence and tests.

### Person profile and anthropometric history

Implemented:

- one-to-one PersonProfile;
- energy-calculation sex, measurement system and energy unit;
- historical AnthropometricMeasurement records;
- metric, value, unit, observed time and provenance;
- persistence and tests.

### Nutrition goals and constraints

Implemented:

- historical NutritionGoal records;
- target weight/rate and validity semantics;
- NutritionConstraint rules with minimum/maximum/exclusion semantics;
- mandatory versus advisory constraints;
- professional provenance and validity periods;
- database validation, persistence and tests.

### Food preferences and adverse reactions

Implemented separately:

- FoodPreference records for likes/dislikes and intensity;
- FoodAdverseReaction records for allergy/intolerance safety semantics;
- provenance and validity dates;
- persistence and tests.

Preference ranking is intentionally separate from food-safety exclusion.

### Person schedule

Implemented:

- recurring and one-off ScheduleEntry shapes;
- availability effects;
- recurrence-rule storage;
- timezone-aware date/time semantics;
- flexibility, location, provenance and notes;
- database validation, persistence and tests.

Detailed semantics: `docs/domain/schedule-model.md`.

### Nutrition targets

Implemented:

- versioned NutritionTarget snapshots per Person;
- optional relationship to NutritionGoal;
- BMR/TDEE estimates and methods;
- target energy range;
- calculation version and input provenance;
- extensible NutritionTargetComponent nutrient targets;
- historical validity and persistence tests.

Detailed semantics: `docs/domain/nutrition-target-model.md` and ADR-008.

### Health connections and normalized measurements

Implemented:

- Person-scoped HealthConnection records;
- provider-agnostic connection lifecycle, permissions and sync metadata;
- secret-free credential references;
- normalized HealthMeasurement records;
- point and interval measurement shapes;
- provider/origin/source-chain provenance;
- deterministic cross-path deduplication;
- historical preservation when a connection is removed;
- persistence and tests.

Detailed semantics: `docs/domain/health-connection-model.md`, `docs/domain/health-measurement-model.md`, ADR-009 and ADR-010.

### Daily health and nutrition state

Implemented:

- versioned DailyHealthState snapshots per Person/local date;
- weight, activity, energy, sleep, heart-rate/HRV and training context;
- confidence and source-window metadata;
- versioned DailyNutritionState snapshots;
- consumed, planned and remaining energy;
- nutrient-level DailyNutritionStateComponent values;
- calculation versions and explainable inputs;
- persistence and tests.

Daily states remain recalculable derived data rather than authoritative source history.

Detailed semantics: `docs/domain/daily-state-model.md` and ADR-011.

### Meal events, participants and servings

Implemented:

- Family-scoped MealEvent records;
- one shared MealEvent with multiple MealParticipant records;
- person-specific participation states;
- multiple Serving records per participant;
- planned, served and consumed quantities and energy;
- ServingNutritionComponent nutrient values;
- replacement history and partial-consumption tracking;
- database constraints, persistence and tests.

There is intentionally no separate SharedMeal table. Shared context lives on MealEvent while nutrition remains person-specific through Serving.

Detailed semantics: `docs/domain/meal-model.md` and ADR-012.

### Food, ingredient and recipe catalogue

Implemented:

- FoodItem identities for ingredients, products, dishes, beverages, supplements and generic foods;
- global or Family-specific catalogue records;
- versioned FoodCompositionSnapshot records;
- extensible FoodNutrientComponent records;
- Recipe and RecipeIngredient records;
- versioned RecipeCompositionSnapshot and RecipeNutrientComponent records;
- optional Serving links to either FoodItem or Recipe;
- historical Serving values protected from later catalogue corrections;
- persistence and tests.

Detailed semantics: `docs/domain/food-catalog-model.md` and ADR-013.

### Serving nutrition calculation

Implemented:

- planned, served and consumed Serving nutrition calculated from explicitly selected versioned Food/Recipe composition;
- Decimal arithmetic with explicit persisted precision;
- safe mass (`mg`, `g`, `kg`) and volume (`ml`, `l`) conversion;
- rejection of unsafe cross-dimension conversions and inferred density;
- persisted exact composition provenance and calculation version;
- reusable composition scaling for recommendation logic;
- tests for scaling, unit conversion safety and catalogue mismatch rejection.

Detailed semantics: `docs/domain/serving-nutrition-calculation.md` and ADR-014.

### Adaptive meal recommendation foundation

Implemented:

- deterministic person-scoped ranking of FoodItem and Recipe candidates;
- candidate nutrition generated from the same versioned composition logic used by Serving calculation;
- ingredient-aware Recipe subject expansion;
- active-date handling for preferences, adverse reactions and constraints;
- mandatory adverse-reaction and food/ingredient/recipe exclusion before ranking;
- mandatory nutrient maxima checked against consumed + already-planned + candidate nutrition;
- fail-closed behaviour for unsupported mandatory constraints or unsafe required unit conversions;
- explainable energy-fit, nutrient-deficit, preference and advisory-reaction scoring;
- deterministic rank ordering, score breakdowns and exclusion reasons;
- versioned recommendation engine identifier;
- tests proving safety rules cannot be overridden by ranking.

Learned ranking is not part of eligibility. Mandatory rules remain authoritative.

Detailed semantics: `docs/domain/adaptive-meal-recommendation.md` and ADR-015.

### Recommendation history and feedback

Implemented:

- person-scoped MealRecommendationRun records for one recommendation execution;
- optional link to the DailyNutritionState used as context;
- engine version, planning date, optional meal type and JSON context;
- MealRecommendationOption snapshots for every eligible and excluded candidate;
- persisted candidate identity, quantity, subjects and exact nutrition snapshot;
- persisted eligibility, rank, score breakdowns, exclusion reasons and explanations;
- optional traceability links to FoodItem/Recipe and exact composition snapshots;
- catalogue/composition links use `ON DELETE SET NULL` while historical snapshots remain intact;
- append-only MealRecommendationFeedback events;
- explicit `accepted`, `rejected` and `modified` actions;
- optional link from feedback to the resulting Serving;
- validation that user feedback only targets eligible options;
- validation that a resulting Serving belongs to the same Person as the recommendation run;
- rejection feedback cannot reference a resulting Serving;
- exact Decimal recommendation values serialized as strings inside JSON snapshots;
- persistence tests for ranked/excluded options and modified feedback.

Feedback is designed as a future learning signal only. It cannot make a candidate eligible or bypass deterministic safety/nutrition rules.

Detailed semantics: `docs/domain/recommendation-feedback-model.md` and ADR-016.

### Recommendation to planned meal materialization

Implemented:

- accepted or modified eligible MealRecommendationOption records materialize into normal MealEvent, MealParticipant and Serving records;
- generated meal records start in `planned` state;
- scheduled timestamps are timezone-aware with explicit MealEvent timezone context;
- accepted recommendations preserve exact recommended quantity/unit;
- quantity/unit changes require `modified` feedback;
- the exact persisted composition snapshot used by the recommendation is reused for Serving nutrition calculation;
- planned Serving nutrition is recalculated through the serving-nutrition service;
- feedback links directly to the resulting Serving;
- ineligible/rejected options cannot create planned meals through this service;
- tests cover accepted materialization, modified quantities and action integrity.

Detailed semantics: `docs/domain/recommendation-to-meal-plan.md` and ADR-017.

### DailyNutritionState recalculation from Serving history

Implemented:

- deterministic recalculation for one Person and one explicit local calendar date;
- IANA timezone local midnight-to-midnight source windows;
- authoritative aggregation from MealEvent/MealParticipant/Serving history;
- cancelled/replaced events, skipped/replaced participants and skipped/replaced servings excluded;
- realized servings contribute consumed values without retaining stale planned values;
- non-realized served portions use served values before planned fallbacks;
- other active non-realized portions use planned values;
- energy totals derived even without a NutritionTarget;
- optional NutritionTarget validated for Person ownership and date applicability;
- nutrient state components materialized from target nutrient components;
- safe explicit unit conversion into target units with failure on unsafe required conversion;
- negative remaining values preserved;
- point nutrient targets represented by equal remaining minimum/maximum values;
- same calculation version recomputed in place without replacing component identities unnecessarily;
- different calculation versions preserved as separate state snapshots;
- source window, Serving IDs/count, target ID and aggregation policy recorded in calculation inputs;
- tests cover consumed/planned aggregation, safe mass conversion, local-day boundaries, served-value precedence, same-version recomputation, version preservation and unsafe-unit rejection.

Detailed semantics: `docs/domain/daily-nutrition-recalculation.md`, `docs/domain/daily-state-model.md` and ADR-018.

### Recommendation practical context

Implemented:

- request-specific PracticalMealContext with timezone-aware intended meal instant;
- ScheduleEntry evaluation at the requested instant;
- one-off non-neutral availability effects take precedence over recurring effects;
- recurring DAILY/WEEKLY rules with optional BYDAY and INTERVAL=1;
- overnight recurring intervals use the date on which the interval begins;
- unsupported recurrence semantics raise explicitly rather than being ignored;
- unavailable schedule windows exclude candidates before ranking;
- preferred/available windows remain explainable in recommendation output;
- explicit request location or unambiguous schedule location can constrain candidate feasibility;
- CandidatePracticalProfile supports available locations, preparation time and kitchen requirement without changing catalogue schema;
- candidates can be excluded for location, insufficient preparation time or unavailable kitchen facilities;
- candidates lacking practical metadata are not excluded merely because metadata is unknown;
- remaining candidates pass through the existing deterministic safety/nutrition recommendation engine;
- practical exclusions remain normal CandidateEvaluation records and are therefore persistable by the existing recommendation-history layer;
- default practical-context engine version is `meal-recommendation-practical-v1`;
- tests cover one-off precedence, recurring preferred windows, location filtering, preparation/kitchen filtering and explicit failure for unsupported recurrence rules.

Detailed semantics: `docs/domain/recommendation-practical-context.md`, `docs/domain/schedule-model.md` and ADR-019.

### Shared-family meal optimization

Implemented:

- one common FoodItem/Recipe candidate can be evaluated for multiple Persons in the same Family;
- each participant receives an explicit person-specific quantity and unit;
- every participant's DailyNutritionState is checked against the corresponding Person;
- Family-specific catalogue candidates are rejected when they belong to another Family;
- existing practical-context, adverse-reaction, mandatory-constraint, nutrition and preference logic is reused independently per Person;
- a shared candidate is eligible only when every participant is individually eligible;
- participant-specific exclusion reasons are preserved in the family-level result;
- unsupported mandatory rules continue to fail closed through the existing engines;
- family ranking first maximizes the minimum participant score and then the average score;
- candidate key provides deterministic final tie-breaking;
- default shared engine version is `shared-family-meal-v1`;
- no new SharedMeal table or schema is introduced;
- tests cover person-specific portions, one-person hard exclusion, fairness-first ranking, one-person schedule exclusion, Family integrity and complete portion coverage.

Detailed semantics: `docs/domain/shared-family-meal-optimization.md` and ADR-020.

### Shared-family meal materialization

Implemented:

- an accepted eligible shared-family recommendation materializes into exactly one planned MealEvent;
- every recommended Person receives one planned MealParticipant and one planned Serving;
- person-specific recommended quantity and unit are preserved exactly;
- planned energy and nutrient snapshots are recalculated through the existing serving-nutrition service;
- the exact persisted FoodCompositionSnapshot or RecipeCompositionSnapshot used by the recommendation is reloaded and reused;
- Persons and composition snapshots must already be persisted, preventing accidental catalogue insertion during meal creation;
- all participants must still belong to one Family and Family-specific catalogue objects must match that Family;
- participant candidate identity and portion values must match the selected family recommendation;
- ineligible family candidates or ineligible participant evaluations cannot be materialized;
- generated MealEvent and Serving records retain recommendation provenance;
- no new SharedMeal table is introduced;
- tests cover one-event/multi-participant materialization, person-specific nutrition, ineligible-candidate rejection, timezone validation and persisted-composition requirements.

Detailed semantics: `docs/domain/shared-family-meal-materialization.md` and ADR-021.

### Meal replacement and idempotency

Implemented on the current feature branch:

- optional MealEvent `idempotency_key` scoped uniquely by Family;
- database-level duplicate prevention for non-null Family/idempotency-key pairs;
- application-level idempotent create that returns the existing MealEvent for an identical retry;
- explicit conflict when one idempotency key is reused with a different request payload;
- complete timezone/source/input validation for idempotent MealEvent creation;
- planned-meal replacement creates a new MealEvent linked through `replaces_meal_event_id`;
- original MealEvent history is preserved and marked `replaced`;
- person-specific MealParticipants, planned Servings and planned nutrient snapshots are cloned into the replacement;
- Food/Recipe and exact composition-snapshot links are preserved in cloned Servings;
- served/consumed values are never copied into replacement plans;
- replacement is rejected after any participant/Serving becomes realized or the event is served/completed;
- replacement retries with the same key/specification return the same replacement rather than cloning again;
- an already-replaced event cannot be replaced again through a different request in this service;
- tests cover idempotent retry, payload conflict, replacement cloning, replacement retry, replacement-chain rejection and served-event rejection.

Detailed semantics: `docs/domain/meal-replacement-idempotency.md` and ADR-022.

## Current database migration chain

The schema currently progresses through:

1. Family/Person;
2. Person profile and anthropometric history;
3. nutrition goals and constraints;
4. food preferences/adverse reactions;
5. schedules;
6. NutritionTarget;
7. HealthConnection;
8. HealthMeasurement;
9. DailyHealthState/DailyNutritionState;
10. MealEvent/MealParticipant/Serving;
11. Food/Recipe catalogue composition;
12. Serving composition provenance;
13. recommendation run/option/feedback history;
14. MealEvent Family-scoped idempotency key.

Recommendation materialization, DailyNutritionState recalculation, practical-context filtering, shared-family optimization and shared-family materialization use the authoritative meal, schedule, catalogue and derived-state schema. Meal replacement/idempotency adds only the MealEvent idempotency key and integrity constraints needed for safe writes.

Alembic migrations are expected to apply from an empty PostgreSQL database in CI and `alembic check` must report no model/schema drift.

## Next planned domain increments

Current sequence after MealEvent replacement/idempotency:

1. restaurant/delivery, pantry and shopping context plus stable persisted practical metadata;
2. API and UI vertical slices over the completed planning flow;
3. background/event-driven DailyNutritionState refresh and target-selection policy;
4. fuller recurrence/calendar override support;
5. persisted family-level recommendation audit history;
6. transaction-level idempotency-race handling at the future write API boundary;
7. learned ranking from feedback only after deterministic hard-rule, practical and nutrition layers remain authoritative.

Each increment must be developed on a focused branch, documented, tested locally with zero warnings, validated by CI and merged only after all checks are green.
