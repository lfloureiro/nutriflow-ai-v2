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

It currently contains 24 ingredients and five recipes selected to exercise catalogue, recipe editing, meal planning, preferences, pantry and shopping workflows:

- Esparguete à bolonhesa
- Chili con carne
- Caril suave de frango
- Salmão no forno com legumes
- Arroz de frango no forno

Names, descriptions, ingredient quantities and units are copied from the v1 snapshot rather than reconstructed from memory.

## Nutrition evidence

The v1 demo snapshot does not contain ingredient nutrition composition. The v2 fixture therefore does not invent kcal or nutrient values.

Imported ingredients have no `FoodCompositionSnapshot` until a user or later import adds authoritative evidence. Imported recipes receive one deterministic recipe composition snapshot whose energy is `null` and whose calculation inputs explicitly record the missing-evidence issue.

This lets the UI and recommendation engine exercise their existing missing-evidence behavior while preserving provenance.

## Provenance and identity

Imported catalogue rows use deterministic UUID5 identities and stable keys:

```text
FoodItem.source = legacy-v1-demo
Recipe.source = legacy-v1-demo
source_reference = nutriflow-ai:v1:demo_3_familias_20_receitas
FoodItem.catalog_key = legacy-v1:ingredient:<legacy id>
Recipe.recipe_key = legacy-v1:recipe:<legacy id>
```

The seed is idempotent. Existing user-added nutrition evidence is not deleted on a later seed run.

## Development command

For normal browser testing use the complete development seed:

```powershell
cd D:\Python\nutriflow-ai-v2\apps\api
python -m app.development_seed
```

This first prepares the existing synthetic Family/health/recommendation demo data and then adds the v1 catalogue subset to the same demo Family.

`python -m app.demo_seed` remains available and preserves its previous narrower semantics for existing automated tests.
