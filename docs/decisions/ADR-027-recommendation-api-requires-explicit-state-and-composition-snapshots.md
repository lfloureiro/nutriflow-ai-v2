# ADR-027: Recommendation API requires explicit state and composition snapshots

- Status: Accepted
- Date: 2026-08-22

## Context

NutriFlow now has a deterministic recommendation engine, persisted recommendation history and versioned DailyNutritionState, FoodCompositionSnapshot and RecipeCompositionSnapshot records. The first recommendation API must expose these capabilities without introducing hidden selection rules that make a decision impossible to reproduce later.

Automatically selecting an unspecified "latest" daily state or composition inside the write endpoint would make the API convenient but ambiguous. A later catalogue correction, recalculation or target change could cause the same request shape to evaluate different source evidence.

The API also needs to preserve the existing safety boundary: Family-specific catalogue data cannot leak across Families, unsafe quantity conversions cannot be guessed, and mandatory exclusions must still run before ranking.

## Decision

The first person-scoped recommendation write endpoint requires callers to provide:

- one explicit persisted DailyNutritionState ID;
- an explicit planning date matching that state;
- one or more candidates, each identified by an explicit FoodCompositionSnapshot or RecipeCompositionSnapshot ID;
- an explicit positive candidate quantity and quantity unit.

The API reloads all referenced records from persistence. It validates Person ownership, Family boundaries, active catalogue objects and unique candidate catalogue keys before invoking the existing deterministic recommendation engine.

A successful request persists one MealRecommendationRun and its complete ranked/excluded MealRecommendationOption snapshots, then returns the persisted run and option IDs together with the evaluation result.

The endpoint does not infer density or cross-dimension quantity conversion. Unsafe candidate scaling is returned as an explicit validation failure.

## Consequences

Positive consequences:

- recommendation requests are reproducible against explicit source snapshots;
- no hidden "latest version" policy is introduced prematurely;
- API results are persisted as audit evidence in the same transaction;
- existing hard-rule-first safety semantics remain authoritative;
- Family isolation is enforced before recommendation;
- future UI clients can retain stable run/option identifiers for feedback and meal materialization.

Trade-offs:

- clients must know which DailyNutritionState and composition snapshots they want to evaluate;
- catalogue/state discovery endpoints are still needed for a complete interactive UI;
- practical schedule, pantry and commercial-source orchestration are not yet included in this first API endpoint;
- automatic candidate generation and quantity selection remain future capabilities.

## Rejected alternatives

### Automatically use the latest DailyNutritionState and catalogue composition

Rejected for the first write API because "latest" is a selection policy, not a neutral lookup, and can reduce reproducibility.

### Accept arbitrary nutrition JSON from the client

Rejected because recommendation should use server-side versioned catalogue evidence and established unit-conversion rules rather than untrusted duplicate nutrition calculations.

### Persist only eligible options

Rejected because excluded candidates and their reasons are important audit evidence and future explanation/learning data.
