# ADR-057: Weekly plan materialization revalidates selection identity and commits atomically

## Status

Accepted for the first explicit weekly-plan materialization slice.

## Context

Weekly proposal generation is intentionally non-persistent. A user may preview a selected week and apply it later, after NutritionPlans, adverse reactions, availability, weekly progress, DailyNutritionState evidence or meal-slot occupancy have changed.

The browser cannot be trusted to submit the nutritional evidence, scores or transformed nutrient values that originally produced a proposal. At the same time, silently applying a newly different server selection would violate user intent.

A week can also contain several MealEvents. Persisting them one by one with independent commits would allow a partially planned week when a later slot fails.

## Decision

The weekly planning API separates preview from materialization.

### Selection identity

The client submits the original weekly proposal inputs plus, for every selected slot:

- `slot_key`;
- base `candidate_key`;
- for a transformed recipe only, `recipe_ingredient_id` and `replacement_food_item_id`.

The client does not submit ranking scores, Plan-Fit evidence, transformation classification or nutrient values.

### Fresh server recomputation

Before persistence, the server recomputes the complete weekly proposal using the current server-authoritative state.

Materialization proceeds only when the newly selected plan has exactly the same slot set and selection identity as the preview accepted by the user.

If the selected candidate or structured transformation changed, the request fails as stale with HTTP 409. Fresh server evidence is used when the identity is unchanged.

### Transformed choices

Transformation proposals generated during the fresh whole-week computation are retained internally as complete server-authoritative evidence.

The selected transformation is materialized directly from that fresh evidence. The transformation engine is not re-run after earlier slots in the same week have already been inserted, avoiding self-counting those newly inserted meals in weekly-frequency progress.

### Atomic persistence

All selected MealEvents are materialized inside one database transaction boundary and committed once.

Existing meal-slot collision rules remain authoritative. If any later slot conflicts or fails, all MealEvents created by the weekly request are rolled back.

Normal shared meals reuse the existing shared-family materializer. Transformed meals reuse the existing transformation persistence model and provenance rules from ADR-055.

## Consequences

- accepting a stale preview cannot silently apply a different week;
- the browser remains presentation-only for nutrition and transformation evidence;
- weekly-frequency evidence is evaluated before persistence rather than incrementally against meals created by the same request;
- transformed nutrition retains the same auditable provenance as individually materialized transformations;
- failure of any slot leaves no partially applied week;
- existing planned meals still cause an explicit conflict rather than implicit replacement.
