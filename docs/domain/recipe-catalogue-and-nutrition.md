# Recipe catalogue and nutrition

## Purpose

Recipes are first-class Family assets used directly by the meal planner. A Recipe is not a free-text meal name: it is an ordered preparation built from catalogue ingredients with traceable nutrition evidence.

## Family recipe workflow

The Family recipe API supports:

- list/search active recipes;
- optionally include inactive recipes;
- create a recipe;
- edit name, description/preparation, yield and serving count;
- add/remove/reorder ingredients;
- edit ingredient quantity, unit and preparation note;
- deactivate/reactivate recipes without destroying historical references.

Routes:

```text
GET    /api/families/{family_id}/recipes
POST   /api/families/{family_id}/recipes
GET    /api/families/{family_id}/recipes/{recipe_id}
PATCH  /api/families/{family_id}/recipes/{recipe_id}
DELETE /api/families/{family_id}/recipes/{recipe_id}
```

`DELETE` is a soft deactivation.

## Nutrition calculation

Every nutrition-relevant Recipe change creates a new `RecipeCompositionSnapshot`.

The calculation is:

```text
RecipeIngredient quantity
+ latest FoodCompositionSnapshot
+ safe unit conversion
-> scaled ingredient composition

all ingredient contributions
-> RecipeCompositionSnapshot
```

The Recipe snapshot stores:

- total energy when all ingredients contain energy evidence;
- nutrients only when evidence exists for every contributing ingredient and units are safely compatible;
- calculation version;
- exact ingredient/composition IDs and data versions used;
- current yield and serving-count inputs;
- explicit calculation issues.

The initial algorithm version is `recipe-nutrition-v1`.

## Missing evidence rule

Missing evidence is never interpreted as zero.

Examples that produce explicit issues:

- ingredient has no composition snapshot;
- ingredient quantity cannot be safely converted to its composition reference unit;
- one ingredient lacks energy data;
- a nutrient is present in only some ingredient compositions;
- nutrient units cannot be safely combined.

A new snapshot is still created when the Recipe definition changes but calculation is incomplete. This prevents the UI or planner from silently presenting a stale old nutrition result as though it described the current Recipe.

## Historical rule

Old Recipe composition snapshots are immutable evidence. Editing ingredients or nutrition creates a new snapshot instead of rewriting old calculations. Existing historical Servings continue to retain the composition provenance used when they were planned/served/consumed.

## Web UX

`Casa -> Receitas` is the default household catalogue screen. The list stays compact. Selecting a Recipe opens a focused editor containing identification/yield, ordered ingredients and calculated nutrition.

The browser does not calculate calories or nutrients. It only displays the server-created snapshot and its issues.
