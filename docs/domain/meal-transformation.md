# Structured Meal Transformation

Structured Meal Transformation converts a Meal Plan-Fit explanation into a concrete, reviewable Recipe modification without mutating the source Recipe.

## v1 boundary

The v1 engine supports one operation:

```text
replace_ingredient
```

Input:

```text
Person
+ planning date
+ meal type
+ Recipe
+ requested Recipe quantity/unit
+ optional DailyNutritionState
```

Output:

```text
baseline MealPlanFit
+ zero or more improving replacement proposals
+ limitations caused by missing/unsafe evidence
```

API:

```text
POST /api/persons/{person_id}/meal-transformations/proposals
```

## Proposal generation

For each RecipeIngredient with an enabled Family `FoodTransformationProfile`:

1. resolve replacement FoodItems in the same `substitution_group`;
2. require visible/active catalogue items and current composition evidence;
3. derive replacement quantity from explicit typical portions when available;
4. reject unsafe unit conversion rather than infer a conversion;
5. calculate a virtual Recipe candidate by subtracting the source ingredient contribution and adding the replacement contribution;
6. evaluate the virtual candidate using the existing Meal Plan-Fit rules and safety gates;
7. keep the proposal only if it measurably improves eligibility, meal Plan-Fit, or daily-target progress.

The source Recipe and its composition snapshots remain unchanged.

## Portion equivalence

Typical portions are explicit metadata, not an implicit same-weight assumption. If source and target profiles contain typical portions, NutriFlow preserves the number of typical portions:

```text
source portions = source Recipe quantity / source typical quantity
replacement quantity = source portions * replacement typical quantity
```

Only safely convertible units are accepted.

## Evidence and safety

Transformation follows the same evidence rules as serving nutrition and Plan-Fit:

- missing evidence is unknown, not zero;
- unsafe conversions are rejected;
- mandatory adverse reactions remain hard gates;
- mandatory nutrition failures/conflicts remain hard gates;
- a better numeric score cannot override a safety block;
- professional guidance remains authoritative over transformation metadata.

## Development example

Development data defines natural yogurt and Greek yogurt in substitution group `cultured-dairy-yogurt`, with explicit synthetic nutrition evidence and a typical portion of 170 g each.

For the demo breakfast Recipe `Iogurte, muesli e banana`:

```text
baseline: protein 14 g, fiber 8 g
mandatory breakfast protein: >= 15 g

Iogurte natural 170 g
-> Iogurte grego 170 g

expected result:
baseline Plan-Fit ~= 96.67%, blocked
transformed Plan-Fit = 100%, eligible
mandatory protein block resolved
```

This data is development-only and is not manufacturer-specific evidence.

## Web surface

The existing Person Nutrition Plan-Fit panel keeps transformation behind progressive disclosure:

```text
Pessoas
-> <Person>
-> Nutrição
-> Adequação ao plano
-> Avaliar
-> Sugerir melhoria
```

The proposal card shows the ingredient replacement, quantities, before/after fit, affected rule count, and whether a mandatory block is resolved.

## Deferred

- accepting/materializing a proposal as a persistent Recipe variant;
- multiple simultaneous ingredient changes;
- add/remove/increase/reduce operations;
- cooking-method transformations;
- cost, pantry and preparation-time optimization;
- learned or AI-generated transformation candidates without explicit evidence;
- automatic semantic equivalence inferred solely from names.

Decision record: `docs/decisions/ADR-039-structured-meal-transformation-proposals.md`.
