# Family meals read models

## Purpose

`Refeições` needs compact Family-level projections without asking the browser to assemble MealEvents, MealParticipants, Person names and Servings through request fan-out.

Two read-only projections serve distinct presentation questions:

- the Family calendar answers what is planned for a local date range;
- the Family meal detail answers what one shared meal contains for each participant.

Neither projection chooses recommendations, changes meal state, infers health meaning or makes safety decisions.

## Family calendar endpoint

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

### Calendar and timezone semantics

`start_date` is interpreted as a calendar date in `Family.timezone`.

The service constructs local-midnight boundaries in that timezone and converts the complete requested range to UTC before querying persisted MealEvents. This preserves local-day boundaries, including DST changes, rather than grouping by UTC date.

Each returned MealEvent is then assigned to its Family-local date.

### Included meal state

Normal planning views include MealEvents with status:

```text
planned
prepared
served
completed
```

`cancelled` and `replaced` events are omitted from the normal calendar view.

This matches the Family Home agenda semantics and keeps superseded/cancelled plans from cluttering the main meal map.

### Calendar response shape

The response includes:

- Family identity/name/timezone;
- requested `start_date` and inclusive `end_date`;
- one entry for every requested calendar day, including days with no meals;
- MealEvent identity, type/title, scheduled instant, timezone, state and location;
- current MealParticipants with Person ID, display-name fields and participant status.

Returning explicit empty days is intentional. A weekly UI should distinguish "this day exists and has no planned meals" without synthesizing missing calendar rows on the client.

The calendar intentionally does not include Serving quantities. A shared meal remains one compact Family row and the user explicitly drills into it for Person-specific portions.

## Family meal detail endpoint

```text
GET /api/families/{family_id}/meals/{meal_event_id}
```

This projection represents one persisted MealEvent and its persisted participant/Serving evidence.

The response includes:

- Family identity/name/timezone;
- MealEvent identity, type/title, scheduled instant, state and location;
- each persisted MealParticipant with Person identity/display-name fields and participant status;
- each participant's persisted Servings;
- for each Serving, item name/type/status, quantity unit and persisted planned/served/consumed quantities and energy values when available.

The detail projection deliberately preserves planned, served and consumed fields separately. It does not overwrite history or collapse lifecycle states into a newly calculated value.

The current frontend chooses the most realized persisted evidence available for concise display (`consumed`, then `served`, then `planned`). That is presentation selection only; it does not alter or derive the server evidence.

A participant with no persisted Serving is returned with an empty `servings` list. Missing portions are not inferred from another participant or from the shared MealEvent.

Unlike the normal calendar, direct detail lookup may expose an exact cancelled/replaced MealEvent when its ID is explicitly requested. This preserves historical inspection without putting inactive events back into the normal agenda.

## Authority boundary

These read models do not compute or infer:

- new Serving quantities;
- nutrition totals or nutrient aggregation;
- recommendation eligibility/ranking;
- safety decisions;
- DailyNutritionState recalculation;
- medical interpretation;
- inferred participants or inferred portions.

All quantities and energy values shown in meal detail are persisted Serving evidence. The browser must not reproduce recommendation, nutrition or safety rules from these projections.

Future explanation/alternative/edit flows should use their own authoritative service semantics rather than expanding this read model into a command surface.

## Isolation and failure behavior

Both endpoints first resolve the requested Family. Unknown Families return `404`.

Calendar MealEvents are constrained by `MealEvent.family_id`, and participants come only from those returned Family MealEvents.

Meal detail is constrained by both `MealEvent.family_id` and `MealEvent.id`. A MealEvent belonging to another Family is therefore indistinguishable from a missing meal and returns `404` (`Meal not found`).

Invalid calendar range sizes fail validation (`422`) rather than silently expanding or truncating the range.

## Why dedicated read models

A seven-day Family calendar spans persisted MealEvent, MealParticipant and Person information. A shared-meal detail additionally spans Person-specific Serving rows.

Returning focused server projections avoids request fan-out and prevents the browser from becoming the authority for timezone boundaries, active-meal filtering, participant membership or Serving ownership.

This follows ADR-034's progressive-disclosure and server-read-model direction.
