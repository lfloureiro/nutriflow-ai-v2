# ADR-022: Meal events use Family-scoped idempotency and immutable replacement history

## Status

Accepted

## Context

NutriFlow meal planning will be called from HTTP APIs, mobile clients, background jobs and recommendation workflows. These callers can retry after network timeouts or repeat commands without knowing whether the first write committed.

Without an explicit idempotency boundary, retries can create duplicate MealEvent records and double-count planned nutrition.

Meal plans also change after creation. Updating an existing planned MealEvent in place would erase the previous plan and make later adherence, recommendation-feedback and audit analysis ambiguous.

The existing meal model already has `replaces_meal_event_id` and a `replaced` status, but did not define a complete application-level replacement or retry contract.

## Decision

MealEvent receives an optional `idempotency_key` with database uniqueness scoped by `family_id`.

A repeated create command with the same Family/key returns the existing MealEvent only when the request-defining fields match. Reusing the key for a different payload is an explicit conflict.

The database unique constraint remains the final duplicate-prevention boundary for concurrent requests.

Planned-meal replacement creates a new MealEvent linked to the old event by `replaces_meal_event_id`. The original event is retained and marked `replaced`.

Replacement clones person-specific planned participants, Servings and planned nutrition snapshots. It does not copy served or consumed values.

Only unrealized `planned`/`prepared` events may be replaced through this planning service. Realized intake is not rewritten through replacement.

Replacement commands are themselves idempotent. A retry of the same replacement key/specification returns the existing replacement. A different replacement command cannot reuse the same key.

## Consequences

Positive consequences:

- API retries can be made safe without duplicate MealEvents;
- planned nutrition cannot be double-counted because of ordinary repeated requests;
- conflicting key reuse is detected rather than silently accepted;
- the previous plan remains available for audit and adherence analysis;
- replacement integrates with existing DailyNutritionState behaviour because `replaced` MealEvents are excluded from active planning totals;
- no separate replacement-history table is required.

Trade-offs:

- a new nullable MealEvent column and unique constraint are required;
- concurrent create races still require transaction-level retry/fetch handling at the future API boundary;
- replacement cloning deliberately applies only before serving/consumption;
- later multi-stage replacement-chain UX may require an additional orchestration service.

## Alternatives considered

### Use `source_reference` as the idempotency key

Rejected. `source_reference` is provenance and is not guaranteed to be unique. Existing recommendation flows can legitimately use repeated provenance formats.

### Mutate the existing MealEvent in place

Rejected. This loses the old plan and weakens explanation, adherence analysis and audit history.

### Store idempotency only in application memory/cache

Rejected. Duplicate prevention must survive process restarts and multiple application instances. The database needs an authoritative uniqueness boundary.

### Permit replacement after serving

Rejected for the planning service. Served/consumed values are historical intake and require correction semantics rather than plan replacement.
