# ADR-024: Pantry stock is Family-scoped operational state

- Status: Accepted
- Date: 2026-08-21

## Context

NutriFlow can already represent FoodItems, Recipes and persisted practical meal sources, but a generic `pantry` availability source cannot answer whether the Family currently has enough of each ingredient to prepare a concrete Recipe quantity.

The planning engine needs quantity-aware stock and expiry while preserving the existing distinction between mutable operational context and immutable historical Serving/recommendation evidence.

## Decision

Introduce `PantryStockLot` as Family-scoped operational stock for one FoodItem.

Each lot stores a stable Family-scoped stock key, quantity/unit, optional location and expiry, observation time, availability state and provenance.

Recipe pantry sufficiency is derived rather than stored. The service:

1. validates Recipe and ingredient Family scope;
2. scales ingredient quantities by the requested batch multiplier;
3. combines duplicate ingredients;
4. ignores unavailable and expired lots;
5. converts only units that the existing serving-nutrition conversion policy declares safe;
6. computes exact missing quantities;
7. emits deterministic in-memory `ShoppingRequirement` values for shortages.

For candidate-level pantry feasibility, Recipe quantity is converted against explicit Recipe yield metadata. Missing or unsafe yield conversion fails explicitly.

## Consequences

### Positive

- pantry feasibility is based on current quantity rather than a coarse availability flag;
- expiry is deterministic at an explicit timezone-aware instant;
- the same conservative unit rules are reused across nutrition and pantry planning;
- missing ingredient quantities can directly feed a future shopping-list workflow;
- pantry stock remains separate from immutable historical meal/recommendation records;
- no new safety bypass is introduced into recommendation ranking.

### Trade-offs

- stock is a current-state model, not a full inventory movement ledger;
- shopping requirements are calculated but not persisted yet;
- Recipe candidates require yield metadata for quantity-aware pantry evaluation;
- cross-dimension conversions remain unsupported even when a real-world density might be known.

## Rejected alternatives

### Store pantry quantity on MealCandidateAvailability

Rejected because practical availability sources describe where/how a candidate can be obtained, while stock is FoodItem-level inventory that may be shared by many Recipes and must support expiry and aggregation.

### Store one aggregate quantity per FoodItem

Rejected because separate lots may have different units, locations, expiries and provenance.

### Infer density for mass/volume conversion

Rejected because silent density assumptions could incorrectly mark a Recipe as feasible. Unsupported conversions must fail explicitly.

### Persist Recipe sufficiency snapshots

Rejected for this increment because sufficiency is derived from mutable stock and requested quantity. Persisting it would create stale duplicated state without an event-driven invalidation model.

## Follow-up

Future increments may add persisted shopping-list lifecycle, stock movements/reservations, substitutions and retailer integrations. Those features must preserve the distinction between mutable operational inventory and immutable meal/recommendation evidence.
