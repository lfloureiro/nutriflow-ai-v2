# Web planning bootstrap API

The first responsive web vertical slice originally required users to paste technical `DailyNutritionState` and composition snapshot UUIDs. This increment adds a read-only server-side bootstrap boundary so the UI can discover the persisted planning evidence needed for a real recommendation flow without allowing the browser to author nutrition evidence.

## Endpoint

```text
GET /api/persons/{person_id}/planning-bootstrap?scheduled_at=<timezone-aware instant>
```

The endpoint is person-scoped and read-only.

## Planning date

`scheduled_at` must be timezone-aware.

The server converts that instant into the persisted Person timezone and derives `planning_date` from the resulting local date. The client does not supply a separate authoritative planning date for bootstrap selection.

An unknown Person timezone fails explicitly rather than silently falling back to UTC or server-local time.

## Daily nutrition state discovery

For the derived local planning date, the endpoint returns the most recently computed persisted `DailyNutritionState` for the Person.

Selection is deterministic:

1. matching `person_id`;
2. matching local `state_date`;
3. latest `computed_at`;
4. then latest persistence timestamp/ID as stable tie-breakers.

The response includes energy progress plus persisted nutrient progress components.

If the requested local date has no persisted state yet, `daily_nutrition_state` is `null`. Bootstrap discovery remains usable for catalogue browsing, but recommendation submission still requires a real persisted state and therefore cannot fabricate one in the browser.

## Candidate discovery

The endpoint returns active FoodItem and Recipe candidates visible to the Person's Family:

- global catalogue objects (`family_id IS NULL`);
- catalogue objects owned by the Person's Family;
- never catalogue objects owned by another Family;
- inactive catalogue objects are excluded.

For each catalogue object, the server returns at most one composition snapshot valid as of `scheduled_at`.

### Food composition selection

A FoodItem composition is eligible only when:

```text
effective_at <= scheduled_at
```

The latest eligible snapshot is returned. Future Food composition evidence is never exposed as current planning evidence.

### Recipe composition selection

A Recipe composition is eligible only when:

```text
computed_at <= scheduled_at
```

The latest eligible snapshot is returned. Future-computed Recipe composition evidence is not used for an earlier planning instant.

## Candidate response

Each candidate exposes the minimum UI-safe evidence required to construct the existing practical recommendation request:

- candidate kind (`food_item` or `recipe`);
- persisted composition snapshot ID;
- catalogue key and display name;
- category;
- optional brand/description;
- reference quantity and unit;
- energy value when available;
- composition version;
- composition evidence timestamp.

The browser may display, filter and let the user choose among these values, but it still submits the returned persisted composition ID to the recommendation API. It does not submit self-authored nutrition totals.

## Safety and isolation

This endpoint does not evaluate recommendation eligibility and cannot override hard rules.

It preserves the existing boundaries:

- Family-scoped catalogue data cannot leak across Families;
- inactive catalogue objects are excluded;
- future composition evidence is not used for an earlier planning instant;
- client-authored nutrition totals remain outside the recommendation trust boundary;
- recommendation safety, practical context and ranking remain authoritative in the existing recommendation services.

## Current limitations

This is intentionally a minimal bootstrap API for the web vertical slice. It does not yet provide:

- text search or pagination for large catalogues;
- meal-type-specific candidate discovery;
- semantic filtering of ingredients versus finished dishes;
- automatic DailyNutritionState recalculation when state is missing;
- automatic NutritionTarget selection;
- provider/live catalogue discovery;
- authenticated current-user/current-family discovery.

Those are separate increments. The immediate consumer is the web UI so users no longer need to paste state/composition UUIDs manually.
