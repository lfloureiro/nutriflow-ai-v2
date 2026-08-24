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
python -m app.fdc_enrichment audit
python -m app.fdc_enrichment audit --all
python -m app.fdc_enrichment list-missing
python -m app.fdc_enrichment search "garlic raw"
python -m app.fdc_enrichment inspect 123456
python -m app.fdc_enrichment apply-map path\to\approved-fdc-mapping.json
```

`audit` is the preferred starting point. It does not call USDA and reports each shared Ingredient's Recipe usage, Recipe units, nutrition status and any remaining unsafe unit conversions. By default it shows blockers only; `--all` includes ready Ingredients.

`list-missing` is a simpler composition-only view. `search` returns candidates. `inspect` shows the nutrition and USDA `foodPortions` for one candidate. `apply-map` is the only operation that writes nutrition, and it accepts explicit FDC IDs only.

## Provenance and versioning

Each approved FDC match creates an immutable `FoodCompositionSnapshot` with:

- 100 g reference quantity;
- kcal energy when available;
- core protein, fat, carbohydrate, fibre and sodium values when present;
- `source = usda-fdc`;
- direct FDC food-details source reference;
- FDC ID, data type, publication date and curation method in notes;
- a deterministic source data version.

Reapplying the same FDC record and conversion is idempotent and does not create another Ingredient composition.

## Safe Recipe-unit conversions

Recipe quantities are not silently coerced to grams. Native mass-to-mass and volume-to-volume conversions continue to use the deterministic serving conversion rules. Cross-dimension or count conversions require explicit evidence.

FoodData Central `foodPortions` may be approved as Ingredient-specific conversions. For example, if an approved FDC record states that one clove weighs 3 g:

```json
{
  "matches": [
    {
      "catalog_key": "legacy-v1:ingredient:4",
      "fdc_id": 123456,
      "unit_portion_id": 789,
      "recipe_unit": "dentes"
    }
  ]
}
```

If the USDA portion itself represents multiple items, NutriFlow uses its `amount` and `gramWeight` to derive grams per one Recipe unit.

For volume-to-mass cases, the curator must also state how many Recipe units the approved FDC portion represents. Example: if an inspected FDC portion represents 240 ml and weighs 236 g:

```json
{
  "matches": [
    {
      "catalog_key": "legacy-v1:ingredient:13",
      "fdc_id": 654321,
      "unit_portion_id": 987,
      "recipe_unit": "ml",
      "recipe_unit_quantity": "240"
    }
  ]
}
```

The stored conversion becomes `236 / 240 g per ml`. Without that explicit quantity, NutriFlow must not interpret a cup or other volume portion as one millilitre.

Multiple approved conversions for the same FDC Ingredient are cumulative. Adding `dentes` and later `c. sopa` for the same FDC food preserves both conversions in the latest composition snapshot.

## Enrichment audit statuses

The audit classifies each active shared Ingredient as one of:

```text
missing_composition
missing_energy
missing_unit_conversion
ready
```

It also reports all Recipe units currently using the Ingredient and the subset that still cannot be converted safely. Results are ordered by blocker class, then by number of active Recipes affected, so curation can focus on the changes with the highest impact.

## Recipe recalculation

After a new shared Ingredient composition or approved portion conversion is added, every active Recipe that references that Ingredient is recalculated through the deterministic Recipe nutrition engine.

This is intentionally incremental. A Recipe remains nutritionally incomplete until every required Ingredient has usable energy evidence and safe unit conversion. Once the final blocker is enriched, the next Recipe composition snapshot contains calculated energy from the Ingredient evidence.

The previous Recipe and Ingredient snapshots remain in history.

## Safety rules

- no fuzzy match is applied without explicit approval;
- no absent kcal value is invented;
- Branded FDC data are not used by this generic importer;
- imported values keep source/version provenance;
- count or volume-to-mass conversions require explicit portion evidence;
- an FDC portion is never assumed to equal one Recipe unit unless that relationship is explicit;
- shared catalogue curation is not exposed as ordinary Family CRUD;
- Family-owned Ingredients continue to use the existing versioned Family editor.
