# Família Loureiro — import from NutriFlow v1

## Source of truth

The development import is pinned to the real NutriFlow v1 repository state rather than a hand-written fixture:

- repository: `lfloureiro/nutriflow-ai`
- commit: `88eae17dc622f023021436317ba18486a99ef344`
- snapshot: `data/dataset_snapshots/20260426_101840Z_backup-actual.json`
- Git blob SHA: `7b62de5235c50021b479a131a6fe7d0dc8784f9a`

The importer verifies the Git blob identity before using a downloaded snapshot and caches the verified JSON under `database/legacy-v1/cache/`. The cache is ignored by Git.

## Imported household

The v1 snapshot contains household `Família Loureiro` with these four members:

- Luis
- Patricia
- Tiago
- Diogo

v2 creates deterministic UUIDs for the Family and Persons. No birth date, weight, height, sex, health state or calorie target is invented because those fields are not present in this v1 snapshot.

## Shared recipe catalogue

All 43 recipes in the pinned v1 snapshot are imported as global shared recipes (`Recipe.family_id = NULL`). Their original names, descriptions and recipe ingredient quantities are preserved.

Only ingredients actually referenced by those recipes enter the v2 food catalogue. Household-shopping items from the old generic v1 ingredient table that are not recipe ingredients are intentionally not imported as food ingredients.

When the v1 source contains an ingredient line without a usable quantity, v2 preserves the line as `1 qb` and adds an explicit import note rather than silently dropping it.

The old five-recipe v2 development subset used the same stable legacy keys but different curated recipe identities. The full importer replaces those rows with the actual pinned v1 identities and removes the old synthetic compositions that no longer match the real recipes.

## Loureiro recipe ratings

All `recipe_preferences` for household 1 are imported against the corresponding deterministic Persons and shared recipe keys. Notes and source timestamps are preserved.

The v1 rating scale is **0–5**. A zero is a real historical value and is preserved as zero; it is not rewritten to one. Consequently the v2 `FoodPreference.intensity` recipe-rating contract now accepts 0–5.

## Nutrition boundary

The real v1 snapshot provides recipe identity and ingredient structure, but it does not contain sufficiently trustworthy nutrient compositions for the current calorie-aware recommendation engine.

Therefore the historical v1 recipes are not assigned invented calorie values by this import. They remain usable as catalogue/history/preference data and can become calorie-ranking candidates after a separate, auditable nutrition-enrichment step.

## Shared breakfast catalogue

Development also seeds a separate global breakfast catalogue with explicit estimated nutrition for one-person portions:

- Café com leite e torrada com manteiga
- Cereais com leite
- Cerelac com leite
- Iogurte com muesli
- Muesli com leite
- Iogurte com cereais
- Iogurte, muesli e banana
- Cereais, leite e banana
- Iogurte grego, muesli e frutos vermelhos
- Muesli, leite e maçã
- Nestum com leite

These breakfast values are deliberately marked `estimated` with medium confidence and a development warning. They are not presented as manufacturer-specific official nutrition.

Each breakfast is a global one-serving recipe and receives a Family planning profile restricted to `breakfast`, making it immediately usable by the calorie-aware recommendation flow for seeded development Families.
