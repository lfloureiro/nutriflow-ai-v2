# Recommendation practical context

## Purpose

Nutrition fit is not sufficient for a useful meal recommendation.

A candidate can be nutritionally appropriate and still be impractical because the Person is unavailable, is in a location where the candidate cannot be obtained, has too little time to prepare it, or does not have access to required kitchen facilities.

This increment introduces a deterministic practical-context layer around the existing meal-recommendation engine.

## Separation from nutrition and safety

The existing recommendation engine remains responsible for:

- mandatory adverse-reaction exclusion;
- mandatory nutrition constraints;
- energy fit;
- nutrient fit;
- preferences;
- advisory reactions.

Practical context is evaluated as an additional eligibility layer before the remaining candidates are passed to the existing recommendation engine.

This separation keeps medical/allergy safety rules independent from schedule or convenience rules.

## PracticalMealContext

`PracticalMealContext` is an in-memory planning input rather than a new database entity.

It contains:

- `scheduled_at` — timezone-aware intended meal time;
- optional explicit `location`;
- optional `available_minutes`;
- optional `has_kitchen` flag;
- zero or more existing `ScheduleEntry` records.

The context is deliberately request-specific. The same FoodItem or Recipe may be practical at home in the evening and impractical at work during a short lunch window.

## CandidatePracticalProfile

Candidate-specific practical metadata is supplied independently through `CandidatePracticalProfile`.

Initial fields are:

- `candidate_key`;
- optional set of `available_locations`;
- optional `preparation_minutes`;
- `requires_kitchen`.

This first increment does not persist these profiles in the catalogue. That avoids prematurely committing practical metadata to FoodItem/Recipe schema before restaurant, delivery, pantry and preparation modelling are defined.

A candidate without a practical profile is not excluded merely because profile metadata is absent.

## Schedule evaluation

The service evaluates ScheduleEntry records at the exact `scheduled_at` instant.

### One-off precedence

Date-specific one-off entries are more specific than recurring entries.

When matching one-off entries provide a non-neutral availability effect, those effects take precedence over recurring availability effects for the same instant.

This allows an exceptional meeting, trip or appointment to block a habitual preferred meal window without modifying the recurring entry.

### Availability effects

Matching effective entries are interpreted as follows:

- `unavailable` blocks meal recommendation at that instant;
- `available` permits the instant explicitly;
- `preferred` permits the instant and adds an explanation that it is preferred;
- `neutral` provides context such as location/event type but does not itself declare availability.

An unavailable schedule instant excludes every candidate before ranking.

### Location

If the request supplies an explicit location, that location is authoritative for candidate filtering.

Otherwise, when the effective matching schedule context yields exactly one location, that location is used as the inferred planning location.

A candidate with `available_locations` is excluded when the resolved planning location is not in that set.

If location is unknown or ambiguous, the engine does not invent one.

## Recurrence support

Recurring ScheduleEntry values remain stored as RFC 5545-style text.

The practical-context evaluator currently interprets a deliberately conservative subset:

- `FREQ=DAILY`;
- `FREQ=WEEKLY`;
- optional `BYDAY` weekday lists using `MO` through `SU`;
- `INTERVAL=1` only;
- optional `RRULE:` prefix.

Recurring intervals may cross midnight. In an overnight interval, the recurrence date is the date on which the interval started.

Unsupported recurrence keys, frequencies, intervals or weekday values raise `UnsupportedRecurrenceRuleError`. The service does not silently ignore a recurrence rule it cannot interpret because doing so could produce recommendations at the wrong time.

Future calendar work can replace or extend this evaluator with fuller RFC 5545 support without changing ScheduleEntry persistence.

## Preparation and kitchen constraints

A candidate is excluded when:

- its `preparation_minutes` exceed `available_minutes`; or
- it requires a kitchen while `has_kitchen` is explicitly false.

Unknown preparation time or unknown kitchen availability is not treated as a negative fact.

This distinction prevents missing metadata from becoming an implicit exclusion while still allowing callers to provide concrete practical constraints when known.

## Recommendation result semantics

Candidates excluded by practical context remain in the RecommendationResult with:

- `eligible = false`;
- no rank;
- no score;
- explicit exclusion reasons.

Examples include:

- `schedule_unavailable`;
- `candidate_unavailable_at_location:Office`;
- `preparation_time_exceeds_available_window`;
- `kitchen_required`.

Candidates that pass practical filtering are ranked by the existing deterministic nutrition/safety engine. Practical context may add explanation markers such as `schedule_preferred_window`, `schedule_available_window`, and `planning_location:<location>`.

The wrapper uses engine version `meal-recommendation-practical-v1` by default so persisted recommendation history can identify the behaviour that produced the result.

## No schema change

This increment adds no database tables or columns.

It consumes existing ScheduleEntry records and in-memory practical profiles. Recommendation persistence already stores eligibility, exclusion reasons and explanations, so practical decisions remain auditable when the result is persisted.

## Future evolution

Planned follow-up work includes:

- shared-family meal optimization across several Persons;
- persisted preparation/availability metadata once pantry, restaurant and delivery domains are designed;
- fuller recurrence support and calendar occurrence overrides;
- automatic derivation of available preparation windows from surrounding schedule intervals;
- travel-aware location context;
- restaurant opening/delivery availability;
- pantry and shopping feasibility.
