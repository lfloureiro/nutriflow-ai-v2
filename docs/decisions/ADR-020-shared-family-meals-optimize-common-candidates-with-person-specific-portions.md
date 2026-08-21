# ADR-020: Shared family meals optimize common candidates with person-specific portions

## Status

Accepted

## Context

NutriFlow must support family meals without flattening individual nutrition requirements into one household target.

A shared dinner may use the same recipe for several people while each Person has a different:

- portion size;
- DailyNutritionState;
- nutrition target;
- allergy/intolerance profile;
- mandatory professional constraint;
- preference profile;
- schedule and practical context.

A family-level average cannot safely decide eligibility because an average can hide a hard exclusion for one participant.

## Decision

Shared-family optimization will treat the common FoodItem/Recipe identity as the shared candidate and evaluate a person-specific portion independently for every participant.

A shared candidate is eligible only if every Person's existing deterministic recommendation evaluation is eligible.

Family ranking is fairness-first:

1. maximize the minimum participant score;
2. then maximize the average participant score;
3. then use candidate key as the deterministic tie-break.

Hard per-Person exclusions are evaluated before family ranking and cannot be overridden by aggregate score.

The initial implementation is an orchestration service over the existing person-level recommendation and practical-context engines. It does not add a new database aggregate or a separate SharedMeal table.

## Consequences

Positive consequences:

- allergies and mandatory constraints remain person-specific and authoritative;
- family convenience does not override individual safety;
- the same dish can have different portion sizes for different people;
- existing recommendation semantics are reused rather than duplicated;
- family ranking is deterministic and explainable;
- the design aligns with one MealEvent plus multiple MealParticipants/Servings.

Trade-offs:

- every shared candidate is evaluated once per participant;
- one participant's hard exclusion makes that proposal unavailable to the whole shared meal;
- the current fairness objective is deliberately simple;
- family-level recommendation audit persistence is deferred because the current MealRecommendationRun is person-scoped.

## Alternatives considered

### Average all participant scores and rank by the mean only

Rejected because a very high score for one participant can hide a poor result for another.

### Merge all Persons into one synthetic household nutrition state

Rejected because it destroys person-specific target, restriction and intake semantics.

### Add a SharedMeal database table for recommendation

Rejected. The authoritative meal model already represents sharing through one MealEvent with multiple MealParticipants. A recommendation orchestration object does not justify duplicating that persistence concept.

### Permit a family score to override one participant's hard exclusion

Rejected. Safety and mandatory nutrition constraints must remain non-negotiable.
