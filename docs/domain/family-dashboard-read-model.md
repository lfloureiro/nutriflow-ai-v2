# Family dashboard read model

## Purpose

The Family Home needs a compact, server-authoritative view of the current day without forcing the web client to fan out across Person, health, nutrition and meal endpoints.

Endpoint:

```text
GET /api/families/{family_id}/dashboard?on_date=YYYY-MM-DD
```

`on_date` is optional. When omitted, the service resolves the current local date from the persisted Family timezone.

## Response scope

The response contains:

- Family identity, name and timezone;
- resolved dashboard date;
- one member entry for every Person in the Family;
- the latest DailyHealthState for that Person/date when one exists;
- the latest DailyNutritionState for that Person/date when one exists;
- current-day MealEvents in the Family local day;
- participant Person IDs for each returned meal.

Member health evidence includes compact fields suitable for Home cards:

- latest weight;
- 7-day and 28-day weight trend;
- steps;
- active energy;
- sleep duration;
- resting heart rate;
- HRV;
- training load;
- confidence and computation timestamp.

Member nutrition evidence includes:

- consumed/planned energy;
- remaining energy range;
- adherence/confidence;
- computation timestamp.

## Selection semantics

For each member and state type, only evidence whose `state_date` equals the dashboard date is considered. If multiple calculation versions exist, the state with the latest `computed_at` is returned.

The service does not silently fall back to another date. Missing current-day evidence is returned as `null`.

Meal filtering uses the Family timezone to calculate the UTC boundaries of the requested local day. Current Home meals include statuses:

- planned;
- prepared;
- served;
- completed.

Cancelled and replaced meals are excluded from the normal Home agenda.

## Non-goals

This endpoint does not:

- create or recalculate DailyHealthState/DailyNutritionState;
- infer a health score;
- infer whether a raw measurement is medically good or bad;
- calculate nutrition/safety eligibility;
- replace detailed Person health, activity, nutrition or meal-history APIs;
- provide authentication/authorization context.

## Client boundary

The web client may choose presentation labels, number/date formatting and which subset of returned evidence is visible on a compact card.

The web client must not convert missing evidence into zero or invent cross-domain scores. Detailed drill-down should navigate to dedicated Person screens rather than expanding the Family Home response indefinitely.
