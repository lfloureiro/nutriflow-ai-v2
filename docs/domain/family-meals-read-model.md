# Family meals read model

## Purpose

`Refeições` needs a compact Family-level calendar view without asking the browser to assemble MealEvents, MealParticipants and Person names through many separate requests.

The Family meals read model provides one server-authoritative date range for presentation. It is a read-only calendar projection: it does not calculate nutrition, choose recommendations, infer health meaning or alter meal state.

## Endpoint

```text
GET /api/families/{family_id}/meals?start_date=YYYY-MM-DD&days=N
```

Parameters:

- `start_date` is optional. When omitted, the server resolves the current date in the persisted Family timezone;
- `days` defaults to 7 and must be between 1 and 14 inclusive.

Typical UI calls:

```text
Hoje   -> days=1, start_date=Family dashboard date
Semana -> days=7, start_date=Monday of the Family-local calendar week
```

The browser may choose which supported range to request for navigation, but the server remains authoritative for which MealEvents belong to each local calendar day.

## Calendar and timezone semantics

`start_date` is interpreted as a calendar date in `Family.timezone`.

The service constructs local midnight boundaries in that timezone and converts the complete requested range to UTC before querying persisted MealEvents. This preserves local-day boundaries, including DST changes, rather than grouping by UTC date.

Each returned MealEvent is then assigned to its Family-local date.

## Included meal state

Normal planning views include MealEvents with status:

```text
planned
prepared
served
completed
```

`cancelled` and `replaced` events are omitted from the normal calendar view.

This matches the Family Home agenda semantics and keeps superseded/cancelled plans from cluttering the main meal map.

## Response shape

The response includes:

- Family identity/name/timezone;
- requested `start_date` and inclusive `end_date`;
- one entry for every requested calendar day, including days with no meals;
- MealEvent identity, type/title, scheduled instant, timezone, state and location;
- current MealParticipants with Person ID, display name fields and participant status.

Returning explicit empty days is intentional. A weekly UI should be able to distinguish "this day exists and has no planned meals" without synthesizing missing calendar rows on the client.

## Authority boundary

This read model does not expose or compute:

- Serving quantities or nutrition totals;
- recommendation eligibility/ranking;
- safety decisions;
- DailyNutritionState recalculation;
- medical interpretation;
- inferred participants.

Shared-meal detail and Person-specific portions remain a later drill-down using authoritative meal/Serving evidence.

The browser must not use this endpoint to reproduce recommendation or nutrition rules.

## Isolation and failure behavior

The endpoint first resolves the requested Family. Unknown Families return `404`.

All MealEvents are constrained by `MealEvent.family_id`, and participants come only from those returned Family MealEvents.

Invalid requested range sizes fail validation (`422`) rather than silently expanding or truncating the range.

## Why a dedicated read model

A seven-day Family calendar spans persisted MealEvent, MealParticipant and Person information. Returning the presentation projection from the server avoids a request fan-out and prevents the browser from becoming the authority for timezone boundaries or active-meal filtering.

This follows ADR-034's progressive-disclosure and server-read-model direction.
