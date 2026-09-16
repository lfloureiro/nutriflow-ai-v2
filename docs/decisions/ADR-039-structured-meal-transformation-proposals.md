# ADR-039: Structured meal transformations are virtual, evidence-based proposals

Status: Accepted

Date: 2026-09-16

## Context

Meal Plan-Fit can explain why a FoodItem or Recipe portion does or does not fit a Person's effective nutrition guidance. The next product requirement is to turn that explanation into concrete modifications such as replacing one ingredient while preserving safety, provenance and the distinction between a proposal and an accepted meal definition.

A transformation engine must not invent equivalences, mutate source recipes silently, or use a second nutrition scoring system that can disagree with Meal Plan-Fit. A high numeric score must also never make an otherwise blocked transformation acceptable.

## Decision

NutriFlow models meal transformation as a deterministic proposal evaluated through the existing Meal Plan-Fit boundary.

For the first slice:

1. the source is an existing Recipe and requested portion;
2. the engine evaluates the unchanged Recipe with Meal Plan-Fit;
3. one RecipeIngredient may be replaced at a time;
4. replacement candidates must belong to the same explicit `substitution_group` in a Family-scoped `FoodTransformationProfile`;
5. typical source/replacement quantities may encode a portion-equivalence ratio, with source provenance retained on the profile;
6. all required FoodItem composition evidence must exist and quantities must be safely convertible;
7. the transformed Recipe is virtual: source ingredient evidence is removed from the candidate nutrition and replacement evidence is added, scaled to the requested Recipe portion;
8. the virtual candidate is evaluated with the same EffectiveNutritionPlan, safety gates and Meal Plan-Fit rules as the original candidate;
9. a proposal is returned only when it demonstrably improves the result: it resolves a hard eligibility block, increases meal Plan-Fit, or improves daily-target progress;
10. the original Recipe is never modified by proposal generation.

The API returns both `before_fit` and `after_fit`, the structured replacement operation, affected rule identifiers, fit-score delta when defined, and whether a mandatory block is resolved.

## Persistence

`FoodTransformationProfile` persists transformation metadata, not a transformed Recipe. It is Family-scoped because practical substitution knowledge can vary between households even when catalogue items are shared.

The initial profile contains:

- `food_item_id`;
- `substitution_group`;
- optional `typical_quantity` + `typical_unit`;
- `auto_transform_enabled`;
- `source` and `source_reference`.

A transformation proposal itself is calculated on demand in v1 and is not persisted.

## Safety and evidence rules

- Missing composition evidence is not treated as zero.
- Unsupported unit conversions are not guessed.
- Mandatory adverse reactions remain independent hard gates.
- Mandatory plan conflicts and mandatory unknown evidence remain blocking through Meal Plan-Fit.
- Transformation profiles do not override professional plan rules.
- Demo transformation evidence must remain explicitly labelled development-only.

## Consequences

This creates a common nutrition reasoning path:

```text
Recipe
-> baseline MealPlanFit
-> structured virtual operation
-> recalculated evidence
-> after MealPlanFit
-> explainable improvement proposal
```

The engine can later add structured operations such as add/remove, quantity changes, cooking-method changes and explicit variant materialization without changing the safety boundary.

## Deferred

- applying a proposal to create a persistent Recipe variant;
- multiple simultaneous ingredient operations;
- automatic cooking-method transformations;
- pantry/cost/preparation-time optimization during transformation;
- AI-generated substitutions without explicit structured evidence;
- automatic equivalence inference from food names alone.
