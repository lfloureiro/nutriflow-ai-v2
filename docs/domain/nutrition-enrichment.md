# Shared ingredient nutrition enrichment

Status: active design contract for `feature/automatic-meal-intelligence`.

## Purpose

Legacy and shared Recipes should become nutritionally usable without requiring a Family user to maintain a second copy of the shared Ingredient catalogue. Shared nutrition is therefore curated globally, while Family-owned Ingredients remain editable through `Casa -> Ingredientes`.

The runtime follows two separate responsibilities:

```text
PortFIR -> nutrition composition
USDA FoodData Central -> safe measurement evidence when needed
```

A measurement source must not silently replace the nutrition source.

## Primary nutrition source: PortFIR

PortFIR is the primary generic-food composition source for the Portuguese catalogue. NutriFlow imports the current supported PortFIR workbook, stores immutable `FoodCompositionSnapshot` records and recalculates active Recipes that use an enriched Ingredient.

Most PortFIR food values use a 100 g reference. Alcoholic beverages use a 100 ml reference and NutriFlow preserves that distinction, so a Recipe using wine in millilitres does not require an invented density conversion.

The PortFIR workbook is cached locally under `.cache/portfir/` for up to 30 days. Opening a Family starts best-effort automatic enrichment in the background. Failure to download or parse PortFIR does not block normal application navigation.

Automatic matching is deliberately conservative:

- exact normalized names are preferred;
- low-risk preparation descriptors such as `cru`, `fresco`, `congelado` and `picado` may be ignored for a core-name comparison;
- a match must exceed the automatic confidence threshold and have a sufficient margin over the next candidate;
- ambiguous matches remain for review;
- an existing newer non-PortFIR composition is never overwritten by automatic PortFIR maintenance.

PortFIR snapshots include the source version and reference unit in their deterministic data version. If a previously imported PortFIR item is later corrected from a 100 g basis to a 100 ml basis, a new immutable snapshot is created and affected Recipes are recalculated.

## Secondary measurement source: USDA FoodData Central

USDA FoodData Central remains available for explicit curation and, when a configured FDC API key is available, for a small conservative set of automatic measurement conversions.

NutriFlow uses only generic `Foundation` and `SR Legacy` records in this workflow. USDA nutrition is not substituted for an existing PortFIR composition merely to obtain a portion weight.

A USDA `foodPortion` may supply evidence such as:

```text
1 clove = 3 g
1 medium onion = 110 g
1 cup olive oil = 216 g
```

For volume measures, NutriFlow first converts the explicit household measure to its known volume and then derives grams per millilitre from the USDA portion. It never assumes that `1 cup = 1 ml` or that `1 ml = 1 g`.

The initial automatic conversion allow-list is intentionally narrow and requires an exact expected USDA food identity. It covers selected common cases such as olive oil in `ml` and garlic, onion, egg, lemon, carrot and peppers in `un`. If the food identity or required portion is not present, no conversion is written.

If no FDC key is configured or FDC is unavailable, PortFIR enrichment still succeeds; unresolved measurement conversions remain blockers.

## Estimated versus exact calculations

A source-backed average portion is useful but is not the same as weighing the actual ingredient. Automatic USDA portion conversions are therefore stored with `estimated = true`.

When a Recipe uses one of those conversions:

- energy can be calculated;
- the Recipe calculation records the exact conversion and source reference;
- `energy_estimated` is true;
- the number of estimated portion conversions is recorded in calculation inputs.

Explicit curator-approved conversions can remain non-estimated when the evidence describes the actual Recipe measurement.

## Qualitative amounts (`q.b.`)

`q.b.` / `quanto baste` is not converted into a fake quantity. It is excluded from the energy sum and the resulting energy is explicitly marked estimated when the remaining quantitative Ingredients are calculable.

Nutrient totals are withheld when a qualitative amount is present because an unknown quantity of salt or another ingredient must not be treated as complete evidence for mandatory nutrient limits.

## Units that remain fail-closed

Native mass-to-mass and volume-to-volume conversions use deterministic conversion rules. Cross-dimension or count conversions require evidence.

Examples that deliberately remain unresolved without more information include:

```text
1 emb -> unknown package weight
1 bottle/can -> unknown package volume when it is not encoded
1 whole chicken -> variable real weight
```

A Recipe can therefore remain incomplete even after its Ingredients have nutritional compositions if one required quantitative unit still lacks safe conversion evidence.

## Background runtime and Web refresh

The Family endpoint:

```text
POST /api/families/{family_id}/nutrition-enrichment/auto
```

runs PortFIR enrichment first and then attempts the safe USDA unit-conversion allow-list. The response reports composition applications, automatic unit conversions and the number of Recipes recalculated.

The Web app invokes this process in the background when a Family is opened. When data change, it emits a Family-scoped nutrition event so the Ingredient and Recipe catalogues refresh without requiring a browser reload.

## Manual audit and curation tools

From `apps/api`:

```powershell
python -m app.fdc_enrichment audit
python -m app.fdc_enrichment audit --all
python -m app.fdc_enrichment list-missing
python -m app.fdc_enrichment search "garlic raw"
python -m app.fdc_enrichment inspect 123456
python -m app.fdc_enrichment apply-map path\to\approved-fdc-mapping.json
```

`audit` does not call USDA. It reports Recipe usage, Recipe units, nutrition status and remaining unsafe conversions. The statuses are:

```text
missing_composition
missing_energy
missing_unit_conversion
ready
```

Manual `apply-map` remains available for cases that cannot be safely automated. It accepts explicit FDC IDs and optional approved portion mappings; it does not fuzzy-apply a candidate.

## Provenance and versioning

Ingredient and Recipe composition snapshots remain immutable. New evidence creates a new version instead of rewriting history. Stored provenance includes, as applicable:

- PortFIR code, version, reference basis and automatic match confidence;
- USDA FDC ID, data type, publication date and direct source reference;
- USDA portion ID, amount, gram weight, description and measure;
- Recipe unit represented by the conversion;
- whether the conversion is estimated;
- calculation issues and exact Ingredient snapshots used by a Recipe.

## Safety rules

- no absent kcal value is invented;
- no count-to-mass or volume-to-mass conversion is assumed without evidence;
- no package weight is inferred from the word `emb`;
- PortFIR remains the preferred generic nutrition source for this Portuguese catalogue;
- USDA portion evidence can augment a PortFIR snapshot without replacing its nutrition values;
- ambiguous automatic matches remain unresolved;
- automatic average portions are labelled as estimates;
- shared catalogue curation is not exposed as ordinary Family CRUD;
- Family-owned Ingredients continue to use the versioned Family editor.
