# ADR-055: Materialized shared recipe transformations preserve base-recipe identity and transformed nutrition provenance

## Status

Accepted for the first materialized shared-Family transformation slice.

## Context

ADR-054 established that one shared physical recipe transformation must still be evaluated independently for every Person. The preview API can therefore classify a replacement as `plan_adapted` or `preference_variant` only after Person-specific safety, NutritionPlan and preference evaluation.

Planning the selected variant introduces a separate persistence problem. The original Recipe and RecipeCompositionSnapshot no longer describe the meal exactly after an ingredient replacement. Reusing the original composition snapshot on a planned Serving would make the nutritional provenance false. Creating a permanent new Recipe for every one-off transformation would also be too heavy for the first slice and would mix a meal-specific decision with catalogue authoring.

## Decision

A materialized shared recipe transformation keeps the original Recipe as the catalogue identity but persists the applied operation separately in `MealTransformationApplication`.

### Revalidation at materialization

The client identifies the selected operation only by:

- `recipe_ingredient_id`;
- `replacement_food_item_id`;
- ordinary meal context and Person-specific serving quantities.

The server recomputes transformation proposals immediately before materialization. It never trusts browser-submitted classification, scores, NutritionPlan evidence or transformed nutrient values.

If the selected operation is no longer present after recomputation, materialization fails. This covers changes in adverse reactions, NutritionPlans, preferences, composition evidence or other hard gates between preview and application.

### Meal and Serving provenance

The resulting MealEvent:

- remains a normal Family MealEvent;
- references the transformation engine through `source_reference`;
- owns one or more persisted `MealTransformationApplication` records.

Each transformed Serving:

- references the base Recipe;
- does **not** reference the original RecipeCompositionSnapshot;
- stores the transformed planned energy and nutrient components calculated by the server;
- uses `nutrition_source = "transformed"`;
- points through `source_reference` to the persisted transformation application.

This prevents a Serving from claiming that the original composition snapshot produced nutrition that actually came from a modified recipe.

### Frozen transformation evidence

`MealTransformationApplication` records the structured replacement operation and the server-authoritative evidence used at application time, including:

- transformation kind;
- source and replacement ingredient identities and quantities;
- substitution group;
- source recipe composition snapshot;
- Person-specific plan/preference improvement summaries;
- NutritionPlan authority state for each participant;
- transformation engine version.

The evidence is historical provenance. Future changes to a Person's plan or preferences do not rewrite an already-planned meal's recorded decision basis.

### Scheduling

Materialization requires timezone-aware `scheduled_at`, and the local scheduled date must match `planning_date` in the Family timezone. Existing meal-slot collision semantics remain authoritative; an occupied slot returns conflict rather than silently replacing the existing meal.

## Consequences

- transformed nutrition is auditable without falsely attributing it to the original recipe composition snapshot;
- the base Recipe remains recognizable in history and planning;
- one-off variants do not pollute the Recipe catalogue;
- safety and NutritionPlan evidence are revalidated immediately before persistence;
- later work can promote frequently reused transformations into explicit Recipe variants without changing existing meal history;
- multi-operation transformations can extend the same application model using ordered operations.
