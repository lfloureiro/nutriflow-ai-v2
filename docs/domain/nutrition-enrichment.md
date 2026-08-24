# Shared ingredient nutrition enrichment

Status: active design contract for `feature/family-catalog-and-profile-editing`.

## Why enrichment is separate from Family editing

Legacy v1 Recipes reference shared Ingredients. Allowing an arbitrary Family to edit those shared Ingredient compositions would silently change nutrition for every Family that can use the shared Recipe catalogue.

Therefore shared nutrition is curated globally, while Family-owned Ingredients remain editable through `Casa -> Ingredientes`.

## Authoritative source

The first supported curation source is USDA FoodData Central (FDC).

NutriFlow uses only generic `Foundation` and `SR Legacy` records for this shared-ingredient workflow. USDA documents Foundation nutrient values on a 100 g edible-portion basis, which matches the reference model used by NutriFlow. Branded foods are deliberately excluded from this generic-ingredient importer.

No Ingredient is matched automatically just because a name looks similar. The workflow requires an explicit approved mapping:

```json
{
  "matches": [
    {
      "catalog_key": "legacy-v1:ingredient:example",
      "fdc_id": 123456
    }
  ]
}
```

## Development workflow

Configure a local API key in the untracked `.env`:

```text
NUTRIFLOW_FDC_API_KEY=...
```

USDA documents the public `DEMO_KEY` for initial exploration with lower rate limits. A normal data.gov API key should be used for regular development.

From `apps/api`:

```powershell
python -m app.fdc_enrichment list-missing
python -m app.fdc_enrichment search "garlic raw"
python -m app.fdc_enrichment inspect 123456
python -m app.fdc_enrichment apply-map path\to\approved-fdc-mapping.json
```

`list-missing` never calls USDA. `search` only returns candidates. `inspect` shows the nutrient values and any USDA portion weights exposed by the selected FDC food. `apply-map` is the only operation that writes nutrition, and it accepts explicit FDC IDs only.

## Provenance and versioning

Each approved FDC match creates an immutable `FoodCompositionSnapshot` with:

- 100 g reference quantity;
- kcal energy when available;
- core protein, fat, carbohydrate, fibre and sodium values when present;
- `source = usda-fdc`;
- direct FDC food-details source reference;
- FDC ID, data type, publication date and curation method in notes;
- a deterministic source data version.

Reapplying the same FDC record is idempotent and does not create another Ingredient composition.

## Safe portion conversions

Legacy v1 Recipes sometimes use count units such as `un`, while the authoritative FDC nutrient composition is per 100 g. NutriFlow must not assume that one unit weighs one gram.

FoodData Central exposes food-specific portion gram weights for some foods. A curator can explicitly approve one of those portions for a Recipe unit by extending the mapping:

```json
{
  "matches": [
    {
      "catalog_key": "legacy-v1:ingredient:meatball",
      "fdc_id": 123456,
      "unit_portion_id": 98765,
      "recipe_unit": "un"
    }
  ]
}
```

The `recipe_unit` defaults to `un` when `unit_portion_id` is provided.

The selected USDA portion is stored inside the immutable composition notes with:

- FDC portion ID;
- original FDC amount and gram weight;
- portion description/modifier;
- derived grams per approved Recipe unit;
- source and source reference.

The Recipe nutrition engine may then convert, for example:

```text
4 un
x 25 g per un
= 100 g
```

before applying the per-100 g nutrient composition.

This conversion is used only when direct unit conversion is impossible. Existing safe conversions such as `mg <-> g <-> kg` continue to take precedence.

A Recipe remains explicitly incomplete when no approved portion conversion exists. The system does not infer a weight from the Ingredient name, average another food, or assume `un = g`.

Volume-to-mass conversion such as `ml -> g` remains fail-closed unless a future curated density/measure conversion provides equivalent authoritative evidence.

## Recipe recalculation

After a new shared Ingredient composition is added, every active Recipe that references that Ingredient is recalculated through the deterministic Recipe nutrition engine.

This is intentionally incremental. A Recipe remains nutritionally incomplete until every required Ingredient has usable energy evidence and safe unit conversion. Once the final blocker is enriched, the next Recipe composition snapshot contains calculated energy from the Ingredient evidence.

When an approved portion conversion is used, its unit, gram equivalent, source and description are copied into the Recipe composition calculation inputs. This keeps the calculation auditable without mutating the historical Ingredient snapshot.

The previous Recipe and Ingredient snapshots remain in history.

## Safety rules

- no fuzzy match is applied without explicit approval;
- no absent kcal value is invented;
- Branded FDC data are not used by this generic importer;
- imported values keep source/version provenance;
- count-to-mass conversion requires an explicitly approved FDC portion;
- unsupported volume-to-mass conversion remains visible as a blocker;
- shared catalogue curation is not exposed as ordinary Family CRUD;
- Family-owned Ingredients continue to use the existing versioned Family editor.
