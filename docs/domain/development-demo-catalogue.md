# Development demo catalogue

NutriFlow v2 remains independent from v1 at runtime. A small, versioned subset of the v1 demo catalogue is copied into this repository only as development fixture data.

## Source

The source fixture is the v1 snapshot:

```text
lfloureiro/nutriflow-ai
data/dataset_snapshots/nutriflow_demo_dataset_3_familias_20_receitas.json
snapshot_name: demo_3_familias_20_receitas
```

The local v2 copy is:

```text
database/legacy-v1/demo_catalog_subset.json
```

It currently contains 24 ingredients and five recipes selected to exercise catalogue, recipe editing, meal planning, preferences, pantry, shopping and recommendation workflows:

- Esparguete à bolonhesa
- Chili con carne
- Caril suave de frango
- Salmão no forno com legumes
- Arroz de frango no forno

Names, descriptions, ingredient quantities and units are copied from the v1 snapshot rather than reconstructed from memory.

## Nutrition evidence

The v1 demo snapshot does not contain ingredient nutrition composition. Imported ingredients therefore remain without a `FoodCompositionSnapshot`; the seed does not pretend that ingredient-level nutrition came from v1.

For browser and recommendation testing only, the five imported recipes receive a **synthetic development-only recipe composition** with energy, protein, fibre and sodium. These values are not represented as v1 data and must not be used as nutritional reference data.

The recipe snapshot records this explicitly:

```text
calculation_version = legacy-v1-demo-synthetic-nutrition-v1
nutrition_source = synthetic-development-fixture
issue = Development-only synthetic nutrition estimate; recipe structure comes from v1, nutrition does not.
```

The composition represents the whole recipe. Planning bootstrap converts it to one default serving per selected Person using `recipe.serving_count`, so a four-serving recipe is not accidentally recommended as four servings per Person.

This development evidence exists so mandatory nutrient constraints and recipe ratings can be exercised end-to-end without weakening fail-safe production behavior for genuinely missing evidence.

## Provenance and identity

Imported catalogue rows use deterministic UUID5 identities and stable keys:

```text
FoodItem.source = legacy-v1-demo
Recipe.source = legacy-v1-demo
source_reference = nutriflow-ai:v1:demo_3_familias_20_receitas
FoodItem.catalog_key = legacy-v1:ingredient:<legacy id>
Recipe.recipe_key = legacy-v1:recipe:<legacy id>
```

The seed is idempotent and upgrades an already-seeded v1 demo recipe snapshot to the current development fixture version. User-created catalogue entries are not touched.

## Development command

For normal browser testing use the complete development seed:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\api
python -m app.development_seed
```

This first prepares the existing synthetic Family/health/recommendation demo data and then adds or updates the v1 catalogue subset in the same demo Family.

`python -m app.demo_seed` remains available and preserves its previous narrower semantics for existing automated tests.
