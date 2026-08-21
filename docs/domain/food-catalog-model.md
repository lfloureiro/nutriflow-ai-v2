# Food and recipe catalogue domain

## Purpose

NutriFlow needs a native catalogue that can describe ingredients, packaged foods, generic dishes and recipes while keeping nutrition composition explainable and historical.

The catalogue must support two different concerns:

1. current reusable food/recipe knowledge used for planning;
2. historical meal/Serving records that must not change when catalogue data is corrected later.

The implemented structure is:

```text
FoodItem
  -> FoodCompositionSnapshot
       -> FoodNutrientComponent

Recipe
  -> RecipeIngredient -> FoodItem
  -> RecipeCompositionSnapshot
       -> RecipeNutrientComponent

Serving
  -> optional FoodItem OR Recipe reference
  -> its own historical quantity/energy/nutrient snapshot
```

---

## FoodItem

`FoodItem` is the stable catalogue identity for a food source.

Supported `food_kind` values are:

- `ingredient`;
- `product`;
- `dish`;
- `beverage`;
- `supplement`;
- `generic`.

Implemented fields include:

- optional `family_id`;
- stable `catalog_key`;
- name;
- food kind;
- optional brand;
- optional description;
- source and source reference;
- active flag;
- timestamps.

A `FoodItem` with no Family is suitable for shared/imported catalogue data. A Family-linked item can represent household-specific/manual data.

`catalog_key` is globally unique and is intended to provide a normalized identity that can also be used by preference, adverse-reaction and planning logic.

Deactivation is preferred over deleting catalogue knowledge that may still be referenced by history.

---

## FoodCompositionSnapshot

Nutrition composition is versioned rather than stored as mutable columns directly on `FoodItem`.

A snapshot defines composition for a reference quantity and unit, for example:

```text
FoodItem: dry pasta
snapshot: label-v2
reference: 100 g
energy: 348 kcal
protein: 12.4 g
carbohydrate: 72 g
```

Implemented fields include:

- `food_item_id`;
- positive reference quantity;
- reference unit;
- optional energy in kcal;
- `data_version`;
- source and source reference;
- effective timestamp;
- notes;
- timestamps.

The combination `(food_item_id, data_version)` is unique.

When a food label, external database or manual correction changes, NutriFlow creates a new snapshot instead of silently rewriting the previous composition.

This provides reproducibility for plans and calculations that used older data.

---

## FoodNutrientComponent

Nutrients other than energy are extensible component records.

Implemented fields include:

- composition snapshot;
- normalized nutrient key;
- non-negative value;
- unit;
- timestamps.

Only one value for a nutrient key is allowed within one composition snapshot.

Example nutrient keys include:

- `protein`;
- `carbohydrate`;
- `fat`;
- `fibre`;
- `sodium`;
- future micronutrients when justified by planning requirements.

The domain does not require every FoodItem to have every nutrient populated. Missing composition data must remain distinguishable from a measured value of zero.

---

## Recipe

`Recipe` is a stable reusable preparation definition.

Implemented fields include:

- optional `family_id`;
- globally unique `recipe_key`;
- name and description;
- optional total yield quantity and unit;
- optional serving count;
- source and source reference;
- active flag;
- timestamps.

A Family-linked recipe can represent a household recipe. A recipe without a Family can later support shared/system/external catalogue content.

Yield quantity and yield unit are stored together. If one is known, the other is required.

---

## RecipeIngredient

`RecipeIngredient` connects a Recipe to a FoodItem.

Implemented fields include:

- recipe;
- FoodItem;
- positive quantity;
- unit;
- optional preparation note;
- deterministic sort order;
- notes;
- timestamps.

A FoodItem referenced by a RecipeIngredient cannot be hard-deleted while that recipe still depends on it. The item should normally be deactivated instead.

The same FoodItem may appear more than once when a recipe needs separate preparation/use steps.

---

## RecipeCompositionSnapshot

Recipe nutrition is derived data and is therefore also versioned.

A snapshot represents nutrition for a reference quantity/unit of the finished recipe and records how it was calculated.

Implemented fields include:

- `recipe_id`;
- reference quantity and unit;
- optional energy in kcal;
- `composition_version`;
- `calculation_version`;
- calculation-input metadata;
- computation timestamp;
- timestamps.

The combination `(recipe_id, composition_version)` is unique.

`calculation_inputs` can record the exact FoodCompositionSnapshot versions used to calculate a recipe, making composition explainable and reproducible.

Example:

```text
Recipe: spaghetti bolognese
composition_version: ingredients-2026-08-20
calculation_version: recipe-calc-v1
inputs:
  pasta -> label-v2
  minced beef -> manual-v1
```

Changing an ingredient composition does not rewrite an existing recipe snapshot. A later calculation creates another version.

---

## RecipeNutrientComponent

`RecipeNutrientComponent` is the recipe equivalent of `FoodNutrientComponent`.

It stores one nutrient value for one RecipeCompositionSnapshot reference quantity.

Values are non-negative and nutrient keys are unique within a snapshot.

---

## Relationship to Serving

Serving now has optional direct catalogue references:

- `food_item_id`; or
- `recipe_id`.

Both cannot be populated simultaneously.

These references use `ON DELETE SET NULL` because Meal/Serving history must survive catalogue cleanup.

The existing Serving fields remain important:

- `item_type`;
- `item_key`;
- `item_name`;
- planned/served/consumed quantities;
- planned/served/consumed energy;
- ServingNutritionComponent values;
- nutrition source/reference.

Those fields form the historical snapshot of what was actually planned/served/consumed.

Therefore a later rename or nutrition correction in the catalogue must not silently rewrite old Serving records.

---

## Composition calculation boundary

This increment stores the catalogue and versioned composition data. It does not yet implement the application service that converts catalogue composition into Serving nutrition.

The next calculation layer will conceptually perform:

```text
FoodCompositionSnapshot or RecipeCompositionSnapshot
+ Serving quantity
+ unit conversion where valid
-> Serving energy
-> ServingNutritionComponent values
```

That service must record which catalogue composition version produced the Serving values.

Unsupported or ambiguous unit conversions must not be guessed.

---

## Relationship to DailyNutritionState

The full chain becomes:

```text
FoodItem composition
        \
         -> Recipe composition
                  \
                   -> Serving snapshot
                           \
NutritionTarget ------------> DailyNutritionState
```

DailyNutritionState remains derived/recalculable.

Food/recipe composition is reusable source knowledge.

Serving remains authoritative history for the person's planned and actual intake.

---

## Next increments

The catalogue enables:

1. serving-nutrition calculation from Food/Recipe composition;
2. normalized unit conversion and serving-size support;
3. adaptive meal planning and recommendation services;
4. restaurant/delivery catalogue sources;
5. pantry and shopping integration;
6. multilingual catalogue names and richer food metadata.
