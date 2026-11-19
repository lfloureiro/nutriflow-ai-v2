# ADR-056: Weekly planning treats safe recipe transformations as distinct selection variants

## Status

Accepted for the first transformation-aware weekly planning slice.

## Context

ADR-054 defines shared-Family recipe transformations as one physical recipe operation evaluated independently for every Person. ADR-055 defines how a selected transformation is materialized without falsely attributing transformed nutrition to the base RecipeCompositionSnapshot.

Weekly planning previously considered only catalogue candidates returned by the shared practical recommendation engine. This creates a gap when a base recipe is ineligible for one Person but a server-authoritative transformation makes the recipe safe and eligible.

A transformed recipe cannot simply replace the base candidate key:

- weekly frequency guidance targets the persisted base Recipe identity;
- repetition accounting should still treat the variant as the same recipe;
- the weekly search must nevertheless distinguish the base recipe from different structured transformations.

## Decision

Transformation-aware weekly planning expands each recipe candidate with up to three server-generated shared transformation proposals before weekly search.

### Scoring

For each transformed proposal, NutriFlow:

- reuses the Person-specific `after_fit` returned by the shared transformation engine;
- rebuilds the transformed candidate nutrition and subjects from persisted structured operation evidence;
- scores the transformed candidate with the same shared practical recommendation evaluator and the same Person practical context used for the base candidate;
- applies the existing weekly-frequency support evaluator to the transformed Plan-Fit.

No transformation-specific nutrition score is invented.

### Selection identity versus recipe identity

`SharedWeeklyPlanningCandidate` gains an internal optional `variant_key`.

- `candidate_key` remains the base Recipe key.
- `variant_key` uniquely identifies the structured replacement for search and deterministic tie-breaking.
- weekly frequency and repeated-candidate accounting continue to use the base Recipe key.

This allows the optimizer to choose among base and transformed variants without changing how the NutritionPlan refers to the recipe.

### Search and hard gates

Transformed candidates enter the same exact/bounded shared weekly search as ordinary candidates. Existing Person-specific logic remains authoritative for:

- mandatory safety and nutrition rules;
- weekly frequency maxima and minima;
- same-day daily nutrient limits;
- shared-Family fairness and score aggregation.

A transformed candidate that is ineligible for any participant is excluded before search.

### API response

When the selected weekly candidate is a transformed variant, the selected choice includes one structured `transformation` object containing:

- transformation kind;
- base Recipe id;
- structured ingredient replacement;
- Person counts for plan/preference improvement;
- server explanation tokens.

The ordinary `candidate_key` remains the base Recipe key.

The weekly review UI may request additional shared transformation proposals explicitly for the selected Recipe using the ADR-054 Family transformation endpoint. This is suggestion-only: requesting alternatives does not mutate the selected weekly choice or materialize a MealEvent. Any future "use this adaptation" action must preserve the structured operation identity and pass through the same server-authoritative weekly revalidation boundary.

## Consequences

- a recipe that is blocked in its base form may still be selected when a safe structured transformation resolves the block;
- weekly frequency rules continue to apply to the actual base recipe identity;
- different transformations do not collapse into one search candidate;
- transformed candidates remain comparable with ordinary candidates because they use the same practical scoring path;
- the existing materialization endpoint from ADR-055 can later consume the selected weekly transformation without trusting browser-generated evidence.
