# ADR-013: Food and recipe composition is versioned

- Status: Accepted
- Date: 2026-08-21

## Context

NutriFlow needs reusable nutrition composition for ingredients, products, dishes and recipes.

Nutrition data changes over time for legitimate reasons:

- product labels change;
- external databases publish corrections;
- a user corrects a manual entry;
- a recipe changes ingredient quantities;
- the recipe-composition algorithm changes;
- different source versions may produce different nutrient values.

At the same time, historical meal records must remain explainable.

If nutrition values were mutable columns directly on FoodItem or Recipe, changing the current catalogue could make an old plan appear to have used values that did not exist when it was created.

## Decision

Food and recipe composition will be stored as immutable/versioned snapshots.

`FoodItem` and `Recipe` provide stable catalogue identities.

`FoodCompositionSnapshot` records nutrition for a reference quantity/unit and is uniquely versioned per FoodItem.

`RecipeCompositionSnapshot` records derived nutrition for a reference quantity/unit and stores both a composition version and the calculation version/inputs used to derive it.

Nutrients are represented by extensible child component records instead of adding a database column for every nutrient.

A Serving may reference either a FoodItem or a Recipe, but the Serving continues to store its own historical item name/key, quantity, energy and nutrient values.

Serving catalogue foreign keys use `ON DELETE SET NULL` so historical intake survives catalogue cleanup.

## Consequences

### Positive

- old nutrition calculations remain reproducible;
- catalogue corrections do not silently change historical meals;
- recipe composition can record the exact ingredient-composition versions used;
- external food sources can be refreshed without destructive replacement;
- new nutrients can be introduced without schema changes to the parent food/recipe tables;
- Serving remains an authoritative snapshot of planned/served/consumed intake.

### Costs

- there may be multiple composition snapshots for one food or recipe;
- application services must select the appropriate/current snapshot;
- recalculating recipe composition creates new versions rather than editing old rows;
- additional logic is required to scale reference composition to Serving quantities and perform unit conversions safely.

## Alternatives considered

### Store mutable nutrient values directly on FoodItem

Rejected because corrections would alter the apparent basis of historical plans and meals.

### Store only nutrition on Serving

Rejected because reusable foods and recipes would have no normalized composition source, forcing repeated manual entry and preventing reliable planning.

### Recalculate recipes dynamically every time

Rejected as the only strategy because results can change when ingredient composition or calculation logic changes. Versioned RecipeCompositionSnapshot records retain the calculation basis while still allowing recalculation.

## Follow-up

The next application layer will select a catalogue composition snapshot, scale it to a Serving quantity, apply explicit supported unit conversions, and write the resulting energy/nutrient values into the Serving snapshot together with provenance for the composition version used.
