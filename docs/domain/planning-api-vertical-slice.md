# Planning API vertical slice

This increment exposes the deterministic person-scoped meal recommendation flow through the HTTP API while preserving the versioned-state and hard-rule-first architecture already implemented in the domain services.

## Endpoint

The first recommendation write endpoint is:

```text
POST /api/persons/{person_id}/meal-recommendations
```

A successful request returns `201 Created` and persists the recommendation run before returning it.

## Request contract

The request identifies one explicit DailyNutritionState and one or more explicit versioned catalogue composition snapshots.

Required fields:

- `daily_nutrition_state_id` — persisted DailyNutritionState used as current nutrition context;
- `planning_date` — must equal the selected state's `state_date`;
- optional `meal_type`;
- `candidates` — one or more candidate definitions.

Each candidate contains:

- `candidate_kind`: `food_item` or `recipe`;
- `composition_id`: FoodCompositionSnapshot or RecipeCompositionSnapshot ID matching the declared kind;
- positive `quantity`;
- `quantity_unit`.

Candidate catalogue keys must be unique within one request because the deterministic recommendation result uses the catalogue key as the candidate identity and final tie-break key.

## Persistence and source-of-truth rules

The endpoint never accepts client-supplied nutrition totals as authoritative evidence.

For each candidate, the server reloads the persisted composition snapshot and generates the nutrition snapshot using the same safe scaling logic used by Serving calculation and the internal recommendation engine.

Before recommendation, the orchestration layer verifies:

- Person exists;
- DailyNutritionState exists and belongs to that Person;
- planning date matches the state date;
- requested composition exists;
- Family-specific FoodItem/Recipe belongs to the Person's Family;
- Recipe ingredients do not reference FoodItems belonging to another Family;
- candidate catalogue object is active;
- candidate catalogue keys are unique;
- requested quantity/unit can be safely scaled without inferred density or cross-dimension conversion.

## Recommendation inputs

The API loads the Person's persisted:

- food preferences;
- adverse reactions;
- nutrition constraints.

It then delegates to the existing `recommend_meals()` engine. The API does not duplicate hard-rule or ranking logic.

This means the same safety properties continue to apply, including mandatory adverse-reaction exclusion, mandatory food exclusions, mandatory nutrient maxima, fail-closed missing mandatory nutrient data and explicit failure for unsupported mandatory semantics or unsafe mandatory conversions.

## Persisted result

Every successful request creates one MealRecommendationRun and one MealRecommendationOption for every evaluation, including excluded candidates.

The API response includes:

- persisted recommendation run ID;
- Person ID;
- DailyNutritionState ID;
- planning date and optional meal type;
- recommendation engine version;
- persisted option ID for every candidate;
- candidate identity and requested quantity;
- eligibility and rank;
- total score and score breakdown;
- exclusion reasons and explanations;
- exact calculated candidate energy/nutrient snapshot.

The persisted run context also records that the request entered through the API and the explicit composition IDs evaluated.

The returned option IDs are intended to become stable handles for later feedback and accepted-recommendation materialization endpoints.

## HTTP error semantics

The first slice uses:

- `404` when the Person, DailyNutritionState or requested composition snapshot does not exist;
- `422` for semantic validation failures such as wrong Person ownership, cross-Family catalogue references, duplicate candidate identities, inactive catalogue objects, unsafe candidate quantity conversion or recommendation-domain validation failures;
- normal FastAPI/Pydantic `422` validation for malformed request shapes.

## Deliberate scope boundary

This endpoint is the first HTTP vertical slice over the recommendation domain. It intentionally does not yet orchestrate:

- schedule/practical-context evaluation;
- pantry quantity sufficiency;
- restaurant/delivery opening hours and price context;
- automatic selection of the latest DailyNutritionState;
- automatic selection of a catalogue composition version;
- automatic candidate discovery;
- automatic portion optimization;
- shared-family recommendation;
- feedback submission or accepted-option materialization endpoints.

Those capabilities should be exposed incrementally so each API contract has explicit source-selection and transaction semantics rather than hiding policy inside one large endpoint.

## Testing

API integration tests cover:

- one persisted run containing both ranked and hard-excluded options;
- DailyNutritionState ownership validation;
- Family isolation for catalogue candidates;
- missing composition handling;
- duplicate candidate-key rejection;
- unsafe mass/volume candidate scaling rejection.

No schema migration is required because the endpoint uses existing recommendation persistence tables.
