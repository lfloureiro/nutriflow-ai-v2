# Practical recommendation orchestration API

This vertical slice exposes the existing deterministic practical-planning layers through one person-scoped recommendation endpoint suitable for the first web UI.

## Endpoint

```text
POST /api/persons/{person_id}/meal-recommendations/practical
```

The endpoint does not replace the base recommendation endpoint. It adds schedule, source, pantry and commercial orchestration before the same hard-rule-first nutrition recommendation engine.

## Request

The request requires:

- persisted `DailyNutritionState` ID;
- `planning_date`, which must match that state;
- timezone-aware `scheduled_at`;
- one or more explicit candidate composition snapshots and candidate quantities/units.

`scheduled_at` must fall on `planning_date` when converted to the selected DailyNutritionState timezone. This prevents a recommendation for one nutritional day from being evaluated against practical context from another local day.

Optional practical inputs:

- meal type;
- explicit location;
- available preparation/delivery window in minutes;
- kitchen availability;
- practical source kinds to consider.

Supported source kinds are:

```text
home
pantry
restaurant
delivery
store
```

Default source kinds are:

```text
home, pantry, restaurant, delivery
```

`store` is opt-in because it usually represents a procurement path rather than an immediately consumable meal source.

## Persisted inputs loaded automatically

The server loads:

- Person preferences;
- adverse reactions;
- mandatory/advisory nutrition constraints;
- Person schedule entries;
- persisted MealCandidateAvailability rows;
- pantry stock when pantry is requested;
- commercial opening windows and active offers for requested commercial source kinds.

The client does not provide nutrition totals, safety outcomes or calculated availability flags.

## Practical source merge

Practical source kinds are alternatives.

For each candidate and requested channel:

- explicit usable source evidence = available;
- explicit unusable source evidence = unavailable;
- absent source evidence = unknown.

The merged candidate profile is available when any requested channel is explicitly available. It becomes explicitly unavailable only when all requested channels have explicit unavailable evidence. Otherwise availability remains unknown and is not itself an exclusion.

This preserves the existing domain rule that unknown operational metadata is not equivalent to a known negative state.

## Pantry channel

Pantry availability combines:

1. quantity-aware pantry stock sufficiency; and
2. optional persisted `pantry` source metadata.

Pantry stock answers whether the candidate quantity can be supplied from current, non-expired stock. Persisted pantry availability can additionally constrain location, preparation time or kitchen requirements.

If persisted pantry-source metadata exists, both stock sufficiency and explicit source availability must allow the pantry path.

Unsafe conversions or unsupported recipe yield scaling fail explicitly with a semantic 422 response.

## Commercial channels

`restaurant`, `delivery` and `store` are evaluated separately.

For each source kind:

- explicit `is_available=false` sources are unusable;
- opening windows are evaluated at `scheduled_at` in each source timezone;
- missing opening windows mean unknown hours, not closed;
- closed known sources are unavailable;
- active provider offers are collected only from usable sources.

The response returns current active offer snapshots with:

- source kind/key and location;
- provider/offer identity;
- item price and currency;
- delivery fee;
- minimum order;
- total known price (`item_price + known delivery_fee`);
- observation time and source reference.

No FX conversion is inferred and price does not alter nutrition eligibility or recommendation ranking.

## Schedule and request context

The merged practical profile is evaluated through the existing `PracticalMealContext` using:

- requested `scheduled_at`;
- explicit request location, or schedule-derived location when unambiguous;
- available minutes;
- kitchen availability;
- persisted Person schedule entries.

Existing practical exclusions remain authoritative, including:

```text
schedule_unavailable
candidate_unavailable
candidate_unavailable_at_location:<location>
preparation_time_exceeds_available_window
kitchen_required
```

The surviving candidates are then evaluated by the existing deterministic nutrition/safety engine. Practical availability never makes a nutrition- or allergy-ineligible candidate eligible.

## Persistence and response

A successful request persists one `MealRecommendationRun` and every resulting `MealRecommendationOption`, including excluded options.

The run context records:

- `entrypoint=practical-api`;
- explicit candidate composition IDs;
- scheduled instant;
- location;
- available minutes;
- kitchen availability;
- normalized source-kind set;
- active commercial offer keys observed during the request.

The response includes:

- persisted run/option IDs;
- eligibility, rank, score, exclusions and explanations;
- exact calculated candidate nutrition;
- requested practical context summary;
- active commercial offer snapshots.

The existing recommendation decision endpoint can then accept, modify or reject an eligible persisted option.

## Current limitations

This increment intentionally does not yet provide:

- automatic catalogue-wide candidate discovery;
- a Food/Recipe catalogue browse/search API for the UI;
- source selection persistence when an option is accepted;
- provider freshness rejection thresholds;
- basket/order creation;
- price-aware optimization;
- persisted shopping-list lifecycle;
- shared-family orchestration API;
- request-level retry idempotency for recommendation decisions.

These are separate vertical slices and must preserve the same deterministic safety boundaries.
