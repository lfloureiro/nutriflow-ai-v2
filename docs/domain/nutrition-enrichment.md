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
python -m app.fdc_enrichment apply-map path\to\approved-fdc-mapping.json
```

`list-missing` never calls USDA. `search` only returns candidates. `apply-map` is the only operation that writes nutrition, and it accepts explicit FDC IDs only.

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

## Recipe recalculation

After a new shared Ingredient composition is added, every active Recipe that references that Ingredient is recalculated through the deterministic Recipe nutrition engine.

This is intentionally incremental. A Recipe remains nutritionally incomplete until every required Ingredient has usable energy evidence and safe unit conversion. Once the final blocker is enriched, the next Recipe composition snapshot contains calculated energy from the Ingredient evidence.

The previous Recipe and Ingredient snapshots remain in history.

## Safety rules

- no fuzzy match is applied without explicit approval;
- no absent kcal value is invented;
- Branded FDC data are not used by this generic importer;
- imported values keep source/version provenance;
- shared catalogue curation is not exposed as ordinary Family CRUD;
- Family-owned Ingredients continue to use the existing versioned Family editor.
