# ADR-023: Persist practical meal availability per Family

- Status: Accepted
- Date: 2026-08-21

## Context

The practical recommendation layer can already consider schedule, location, preparation time and kitchen access, but candidate practical profiles are currently passed in memory with each request. Restaurant, delivery, pantry and store-aware planning needs durable Family-specific knowledge about where a FoodItem or Recipe can actually be obtained.

Putting these fields directly on FoodItem or Recipe would be incorrect because availability is contextual: the same global catalogue item may be available to one Family through delivery, another only at home, and another not at all. It would also conflate stable food identity/composition with operational sourcing state.

## Decision

Introduce `MealCandidateAvailability` as a Family-scoped operational record linked to exactly one FoodItem or Recipe.

Each record stores a supported source kind (`home`, `pantry`, `restaurant`, `delivery`, `store`), stable source key, optional location, optional preparation/lead time, kitchen requirement, current availability and provenance.

Persisted records are adapted into the existing `CandidatePracticalProfile` interface rather than creating a second recommendation engine.

A candidate with no persisted rows remains unknown and is not excluded solely due to missing metadata. Once availability is explicitly modeled for a candidate/source selection, a lack of any currently usable row means the candidate is unavailable for that request.

## Consequences

Positive consequences:

- global FoodItem/Recipe identity remains independent of Family-specific sourcing;
- the existing deterministic practical filtering path remains authoritative;
- restaurant/delivery/home/pantry/store planning can use one normalized source abstraction;
- explicit unavailability becomes explainable and persistable as a normal recommendation exclusion;
- future provider synchronization can update operational rows without mutating historical meal or recommendation snapshots.

Trade-offs:

- availability rows represent current operational state rather than historical evidence;
- quantity-level pantry stock, expiry, shopping requirements, prices and opening hours require later models/services;
- multiple source rows must be aggregated deterministically before recommendation.

## Rejected alternatives

### Put practical fields directly on FoodItem or Recipe

Rejected because location, delivery and household availability are Family-specific and time-varying rather than intrinsic catalogue properties.

### Treat missing metadata as unavailable

Rejected because existing catalogues may not yet be fully enriched. Missing operational data remains unknown; only explicit modeled unavailability excludes a candidate.

### Let provider/restaurant availability bypass the recommendation engine

Rejected. Availability only determines practical feasibility. Mandatory adverse-reaction and nutrition rules remain independent and cannot be bypassed by any source/provider state.
