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

## Current feature branch: planning API vertical slice

Branch: `feature/planning-api-vertical-slice`.

Merge base / current integrated `main`:

```text
09ca2f235d770b87f128dc8448fe9768b2801ad2
```

Schema head remains:

```text
a7c4e9f2b6d1
```

This branch has no schema change.

Implemented on the branch:

- `POST /api/persons/{person_id}/meal-recommendations`;
- explicit persisted DailyNutritionState selection;
- planning date must match the state date;
- explicit FoodCompositionSnapshot/RecipeCompositionSnapshot IDs per candidate;
- positive requested candidate quantity and explicit unit;
- server-side candidate nutrition calculation using established scaling rules;
- persisted Person preferences, adverse reactions and constraints loaded automatically;
- Person/state ownership checks;
- Family isolation for FoodItem, Recipe and Recipe ingredient catalogue objects;
- inactive catalogue candidate rejection;
- duplicate catalogue candidate-key rejection;
- unsafe quantity scaling mapped to semantic API validation failure;
- successful request persists one MealRecommendationRun and all eligible/excluded MealRecommendationOption rows;
- response exposes persisted run/option IDs, ranks, scores, exclusions, explanations and exact candidate nutrition;
- explicit composition IDs are recorded in persisted recommendation context;
- six API integration tests cover success/persistence and the main boundary failures.

Detailed semantics: `docs/domain/planning-api-vertical-slice.md`, ADR-027.

Expected complete local test suite after this branch:

```text
78 tests
```

## Safety and correctness invariants

Future work must preserve:

- mandatory adverse reactions and mandatory constraints before ranking;
- learned ranking can reorder eligible candidates only;
- unknown candidate nutrient data cannot satisfy a mandatory nutrient maximum;
- unsupported mandatory semantics and unsafe required conversions fail closed;
- no inferred density;
- exact versioned composition provenance for Serving/recommendation decisions;
- recommendation API inputs reference persisted source snapshots rather than client-authored nutrition totals;
- DailyNutritionState remains derived from authoritative meal history;
- Family-scoped data cannot leak across Families;
- shared meals retain person-specific portions and safety checks;
- retries/replacements remain idempotent and historically traceable;
- commercial availability/price cannot make a safety-ineligible candidate eligible;
- warnings are treated as test failures rather than suppressed casually.

A separate future policy may be needed if a mandatory nutrient maximum applies but historical DailyNutritionState cannot represent the current consumed/planned total for that nutrient. Do not silently assume missing historical state is complete evidence.

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

After the current recommendation API branch is locally green, PR-tested and merged:

1. recommendation feedback and accepted-option materialization API endpoints;
2. practical schedule/source/pantry/commercial recommendation orchestration API;
3. first responsive web UI vertical slice;
4. persisted shopping-list lifecycle when UI/API workflows require durable shopping state;
5. background/event-driven DailyNutritionState refresh and explicit target-selection policy;
6. fuller recurrence/calendar override support;
7. persisted family-level recommendation audit history;
8. transaction-level idempotency-race handling at the write API boundary;
9. provider connectors/live freshness policy, basket/order lifecycle and commercial optimization;
10. learned ranking from feedback only after deterministic safety, practical and nutrition layers remain authoritative.

Every increment follows ADR-007: focused branch, code/migration/tests/docs together, local PostgreSQL validation, zero-warning Ruff/pytest, PR only after local green, CI on the exact PR head SHA, guarded squash merge, verify resulting `main`, then start the next branch.
