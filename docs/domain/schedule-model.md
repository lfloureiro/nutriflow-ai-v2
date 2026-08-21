# Schedule domain model

## Purpose

NutriFlow needs time context to decide when a Person can eat, train, commute, work, sleep or participate in shared meals.

The schedule domain is not intended to replace a calendar product. Its role is to provide nutrition-planning context with enough structure to represent both habitual recurring patterns and date-specific events.

## ScheduleEntry

`ScheduleEntry` belongs to one `Person`.

A schedule entry records:

- `person_id`;
- `entry_type`;
- `event_type`;
- `availability_effect`;
- time information appropriate to the entry type;
- timezone;
- flexibility;
- optional location;
- source/provenance;
- optional notes;
- timestamps.

## Entry types

Two entry types are implemented initially.

### Recurring

A recurring entry represents a habitual pattern such as:

- work from Monday to Friday;
- school hours;
- regular training sessions;
- usual sleep period;
- habitual meal windows;
- recurring family commitments.

Recurring entries use:

- `local_start_time`;
- `local_end_time`;
- `recurrence_rule`;
- `valid_from`;
- optional `valid_until`;
- explicit `timezone`.

`recurrence_rule` is stored as a text rule compatible with an RFC 5545-style recurrence representation. The domain model does not hard-code weekdays into database columns, allowing recurrence behaviour to evolve without schema changes.

A recurring interval may cross midnight. For example, sleep from 23:00 to 07:00 is valid, so the database deliberately does not require `local_end_time` to be later than `local_start_time`.

### One-off

A one-off entry represents date-specific context such as:

- an exceptional work meeting;
- a restaurant booking;
- a medical appointment;
- a single workout;
- travel;
- a family event;
- a date-specific change to normal availability.

One-off entries use timezone-aware `starts_at` and `ends_at` timestamps.

The database requires `ends_at > starts_at`.

## Date-specific precedence

When recurring and one-off information conflict for the same time window, date-specific one-off information is considered more specific and should be evaluated first by planning logic.

This allows exceptional events to alter the effective schedule without modifying or deleting the underlying recurring pattern.

The first persistence model does not yet implement an explicit recurrence-occurrence cancellation table. If later calendar synchronization requires precise cancellation or replacement of one generated occurrence, that behaviour can be introduced as a dedicated schedule override entity.

## Availability effect

`availability_effect` describes how the event should influence nutrition planning.

Initial values are:

- `neutral` — provides context without directly declaring availability;
- `available` — explicitly indicates an available period;
- `unavailable` — blocks or strongly discourages meal scheduling in that period;
- `preferred` — marks a preferred period for meal or planning activity.

This is deliberately separate from `event_type`. A work event may be unavailable, while a habitual lunch event may mark a preferred meal window.

## Event type

`event_type` remains an extensible domain key rather than a fixed database enum.

Expected values include:

- work;
- school;
- commute;
- sleep;
- training;
- meal_window;
- family_commitment;
- travel;
- other future planning contexts.

New event categories can therefore be introduced without a migration when they do not require new structural behaviour.

## Flexibility

`flexibility_minutes` records how far a planned activity can reasonably move around the represented time.

Examples:

- `0` for a fixed appointment;
- `15` for a moderately flexible lunch window;
- `30` for a workout that can shift within the evening.

The value is non-negative.

## Timezones

Every schedule entry stores an explicit timezone.

This prevents a recurring local-time pattern from silently changing meaning if the Person later changes their profile timezone or travels.

One-off timestamps remain timezone-aware absolute timestamps while the timezone field preserves the local planning context.

## Provenance

Initial provenance fields are:

- `source`;
- `source_reference`.

Manual entries default to `user`.

Future calendar integrations can use values such as external provider names and preserve an external event identifier in `source_reference`.

## Database integrity

The database enforces:

- only `recurring` and `one_off` entry shapes;
- valid availability-effect values;
- non-negative flexibility;
- valid one-off timestamp ordering;
- valid recurring date-range ordering;
- mutually exclusive recurring and one-off time representations;
- cascade deletion when the owning Person is removed.

## Future integration

The schedule model will later provide context to:

- derived nutrition targets;
- meal planning;
- shared family meals;
- individual Serving timing;
- workout-aware recommendations;
- restaurant/delivery planning;
- external calendar synchronization.

Schedule data describes planning context. It does not itself calculate calorie or nutrient targets.
