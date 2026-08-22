# Recommendation practical context

## Purpose

Nutrition fit is not sufficient for a useful meal recommendation. A candidate can be nutritionally appropriate and still be impractical because the Person is unavailable, is in the wrong location, lacks preparation time/kitchen access, has insufficient pantry stock, or cannot currently obtain the item from a modeled restaurant/delivery/store source.

The practical-context layer is deterministic and runs before the existing nutrition/safety ranking engine.

## Separation from nutrition and safety

The nutrition/safety engine remains authoritative for:

- mandatory adverse-reaction exclusion;
- mandatory NutritionConstraint rules;
- energy/nutrient fit;
- preferences;
- advisory reactions.

Practical context can make a candidate ineligible, but it can never make an otherwise safety-ineligible candidate eligible.

## PracticalMealContext

`PracticalMealContext` is request-specific and contains:

- timezone-aware `scheduled_at`;
- optional explicit `location`;
- optional `available_minutes`;
- optional `has_kitchen`;
- zero or more ScheduleEntry records.

The same candidate may therefore be practical at home in the evening and impractical at work during a short lunch window.

## CandidatePracticalProfile

Candidate-specific practical feasibility is normalized through `CandidatePracticalProfile`.

Current fields:

- `candidate_key`;
- optional explicit `is_available`;
- optional `available_locations`;
- optional `preparation_minutes`;
- `requires_kitchen`.

A missing profile means practical metadata is unknown rather than unavailable.

Profiles can now come from several deterministic sources:

- request-local caller metadata;
- persisted `MealCandidateAvailability` source rows;
- quantity-aware pantry sufficiency;
- time-aware restaurant/delivery/store commercial-source evaluation.

These sources all adapt into the same practical interface rather than creating competing recommendation engines.

Detailed source semantics:

- `docs/domain/persisted-practical-availability.md`;
- `docs/domain/pantry-stock-shopping-requirements.md`;
- `docs/domain/restaurant-delivery-commercial-context.md`.

## Schedule evaluation

ScheduleEntry records are evaluated at the exact intended meal instant.

### One-off precedence

When matching one-off entries have a non-neutral availability effect, they take precedence over matching recurring effects. A date-specific meeting/trip can therefore block a habitual preferred meal window without changing the recurring schedule.

### Availability effects

- `unavailable` blocks recommendation at that instant;
- `available` permits it explicitly;
- `preferred` permits it and adds an explanation marker;
- `neutral` contributes contextual information such as location/event type without declaring availability.

An unavailable schedule instant excludes all candidates before ranking.

### Location

An explicit request location is authoritative. Otherwise, exactly one location derived from effective schedule context may be used.

If a candidate/profile has restrictive available locations and the resolved location is outside them, the candidate is excluded. Unknown/ambiguous location is not invented.

## Recurrence support

Schedule recurrence uses a conservative interpreted subset of stored RFC 5545-style text:

- `FREQ=DAILY`;
- `FREQ=WEEKLY`;
- optional `BYDAY` using `MO` through `SU`;
- `INTERVAL=1` only;
- optional `RRULE:` prefix.

Overnight intervals belong to the date on which the interval starts.

Unsupported keys/frequencies/intervals/weekdays raise `UnsupportedRecurrenceRuleError`; recurrence is never silently ignored.

## Preparation and kitchen constraints

A candidate is excluded when:

- explicit profile availability is false;
- preparation time exceeds the available window;
- a kitchen is required while kitchen access is explicitly false;
- resolved location is outside restrictive available locations.

Unknown values are not treated as negative facts.

## Pantry-derived feasibility

`build_pantry_stock_practical_profiles()` evaluates FoodItem or Recipe candidate quantities against current Family pantry stock.

A pantry-derived profile is explicitly available only when required quantities are satisfied under safe unit-conversion rules. Unsafe cross-dimension comparison fails explicitly; no density is inferred.

## Commercial-source feasibility

`build_commercial_planning_context()` evaluates modeled restaurant/delivery/store sources at a timezone-aware planned instant.

Commercial source opening windows can make a modeled source closed. Missing opening-window data remains unknown rather than closed. Active provider offers are returned separately from practical profiles: missing current price data does not by itself make an otherwise open source unavailable.

Commercial price never bypasses safety/nutrition rules and is not currently part of ranking.

## Recommendation result semantics

Practical exclusions remain normal `CandidateEvaluation` records with:

- `eligible = false`;
- no rank;
- no score;
- explicit exclusion reasons.

Examples include:

- `schedule_unavailable`;
- `candidate_unavailable`;
- `candidate_unavailable_at_location:<location>`;
- `preparation_time_exceeds_available_window`;
- `kitchen_required`.

Candidates that pass practical filtering continue through deterministic safety/nutrition ranking. Explanations can include `schedule_preferred_window`, `schedule_available_window` and `planning_location:<location>`.

The wrapper engine version remains `meal-recommendation-practical-v1` unless a future behaviour change deliberately introduces a new version.

## Persistence boundary

The original practical-context wrapper itself did not require schema changes. Later increments added operational persistence around it:

- MealCandidateAvailability — ADR-023;
- PantryStockLot — ADR-024;
- MealSourceOpeningWindow/MealCommercialOffer — ADR-025.

Recommendation history already persists resulting eligibility, exclusions and explanations independently from operational source rows.

## Future evolution

Remaining planned work includes:

- fuller recurrence/calendar override support;
- automatic derivation of preparation windows from surrounding schedule intervals;
- travel/geographic routing context;
- provider live-freshness policies and connectors;
- basket/order workflows and deliberate commercial optimization;
- API/UI vertical slices that compose schedule, pantry, source and deterministic nutrition context coherently.
