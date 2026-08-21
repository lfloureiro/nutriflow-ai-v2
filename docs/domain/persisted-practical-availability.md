# Persisted practical meal availability

NutriFlow needs practical meal planning to use durable data rather than only request-local `CandidatePracticalProfile` objects. This increment persists Family-scoped ways in which a FoodItem or Recipe can be obtained or prepared and adapts them into the existing deterministic practical recommendation layer.

## MealCandidateAvailability

`MealCandidateAvailability` represents one Family-specific availability source for exactly one FoodItem or Recipe.

Supported source kinds are:

- `home` — a meal that can be prepared or obtained at home;
- `pantry` — a food/meal currently represented as available from household stock;
- `restaurant` — an eat-at-venue option;
- `delivery` — an option obtainable through delivery;
- `store` — an option obtainable from a shop or other retail source.

Each row records:

- Family ownership;
- exactly one FoodItem or Recipe reference;
- source kind and a stable `source_key` identifying the concrete source;
- optional location;
- optional preparation/lead time in minutes;
- whether a kitchen is required;
- explicit current availability;
- source provenance, external reference and notes.

The catalogue reference uses `ON DELETE CASCADE` because these rows are current operational availability, not historical recommendation evidence. Historical recommendation/Serving records continue to preserve their own snapshots and provenance independently.

## Adapting persisted availability to practical profiles

`build_persisted_practical_profiles()` loads availability for one Family and a set of persisted meal candidates, then produces normal `CandidatePracticalProfile` objects consumed by the existing practical recommendation engine.

Aggregation rules are deterministic:

- rows are Family-scoped;
- a Family-specific FoodItem/Recipe from another Family is rejected;
- candidates with no persisted availability rows remain `unknown` and therefore preserve the previous behaviour of not being excluded merely because metadata is missing;
- when rows exist but none are currently available, the profile is explicitly unavailable and the practical engine excludes the candidate;
- callers may restrict the lookup to one or more source kinds, such as delivery-only planning;
- if the requested source kind is known for the candidate but no row in that kind is available, the candidate is explicitly unavailable for that request;
- preparation time is the minimum non-null time across currently usable sources;
- kitchen requirement is true only when every currently usable source requires a kitchen;
- locations are restrictive only when every currently usable source has an explicit location. A source without a location is treated as not location-restricted.

## Safety boundary

Persisted practical availability affects feasibility before nutrition ranking. It does not modify allergy, intolerance or mandatory NutritionConstraint semantics. A candidate that passes availability checks still goes through the existing hard-rule-first recommendation engine.

`CandidatePracticalProfile.is_available=False` produces the normal exclusion reason `candidate_unavailable`.

## Current limitations

This increment intentionally does not yet model:

- pantry quantities or expiry at ingredient level;
- recipe ingredient sufficiency calculations;
- shopping-list generation;
- prices, fees, minimum orders or delivery ETAs that change in real time;
- restaurant opening hours;
- provider API synchronization;
- geographic distance/routing.

Those capabilities can build on the stable source records without weakening deterministic safety or recommendation history.

## Next steps

1. add quantity-aware Family pantry stock and expiry;
2. calculate recipe ingredient sufficiency and missing quantities;
3. materialize missing quantities into shopping requirements;
4. add restaurant/delivery price, opening-hours and provider synchronization policies;
5. expose source filters and practical availability through API/UI vertical slices.
