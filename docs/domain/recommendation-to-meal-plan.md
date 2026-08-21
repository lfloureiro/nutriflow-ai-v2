# Recommendation to meal plan materialization

## Purpose

This increment closes the loop between an eligible persisted recommendation and the authoritative planned-meal domain.

A recommendation is not itself a meal plan. It is a ranked decision artifact. Once the user accepts or modifies an eligible recommendation, NutriFlow materializes that decision as normal `MealEvent`, `MealParticipant` and `Serving` records.

## Materialization flow

The implemented flow is:

```text
MealRecommendationRun
  -> MealRecommendationOption
  -> accepted / modified decision
  -> MealEvent
  -> MealParticipant
  -> Serving
  -> MealRecommendationFeedback(resulting_serving)
```

The generated meal records are ordinary authoritative planning records. Downstream daily-state calculation must consume the `Serving`, not the recommendation option.

## Accepted versus modified

`accepted` means the recommended quantity and unit are preserved.

If quantity or unit changes, the action must be `modified`. This distinction preserves useful feedback for later ranking and learning.

Other planning context such as schedule, location or title may be supplied during materialization without changing the recommended food quantity.

## Exact composition provenance

The persisted recommendation option already points to the exact versioned `FoodCompositionSnapshot` or `RecipeCompositionSnapshot` used for recommendation.

Materialization requires exactly one of those composition snapshots. The planned `Serving` is recalculated from that same snapshot using the normal serving-nutrition calculation service.

This prevents a recommendation from being accepted using one nutrition basis and silently materialized using a newer catalogue version.

## Planned state

Materialization creates:

- `MealEvent.status = planned`;
- `MealParticipant.status = planned`;
- `Serving.status = planned`;
- `Serving.quantity_planned` from the accepted or modified quantity;
- planned energy and nutrient values recalculated from the exact composition snapshot.

No served or consumed values are invented.

## Safety boundary

Only recommendation options that were already marked eligible can be materialized.

Rejected options do not create meal records through this service. Ineligible options can never create a meal plan through this path.

The recommendation engine remains responsible for mandatory safety and nutrition filtering before an option becomes eligible.

## Feedback linkage

The accepted or modified feedback event is created with a direct reference to the resulting `Serving`.

This provides a stable audit path from:

- what the engine recommended;
- what the user decided;
- what was actually placed into the meal plan.

## Time semantics

The caller must provide a timezone-aware `scheduled_at` timestamp and an explicit timezone string for the `MealEvent`.

The service does not infer the local timezone from the database server.

## Future evolution

Later increments may add:

- idempotency keys for API retries;
- replacement semantics when an already-planned recommendation is modified later;
- shared-family materialization for one recommendation decision affecting multiple people;
- schedule conflict handling before materialization;
- automatic DailyNutritionState recomputation after plan changes;
- API contracts and UI actions around accept/modify/reject.
