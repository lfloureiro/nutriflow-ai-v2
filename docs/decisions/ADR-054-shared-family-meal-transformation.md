# ADR-054: Shared Family meal transformations remain Person-specific in evidence

## Status

Accepted for the first shared-Family transformation slice.

## Context

NutriFlow already supports structured Person-level recipe transformations, beginning with ingredient replacement inside persisted substitution groups. Weekly Family planning needs to adapt a common recipe without pretending that every participant has the same NutritionPlan, serving size, preferences or safety constraints.

A Family-level transformation therefore cannot be evaluated once and copied to every Person. The physical recipe change is shared; the nutritional and safety consequence is Person-specific.

ADR-053 established that NutritionPlan authority is explicit and derived. A generic nutrient difference, preference signal or standalone safety rule does not by itself justify a claim that a recipe is `better` or `aligned with the plan`.

## Decision

A shared transformation consists of one structured recipe operation applied to the common recipe and independently evaluated for every participant using that Person's serving quantity, DailyNutritionState, active NutritionPlan evidence, preferences and adverse reactions.

The first supported operation remains `replace_ingredient`. The operation is generated only from persisted `FoodTransformationProfile` substitution groups and nutrition composition evidence. Ingredient names are never used to infer equivalence or nutrition.

### Participant-specific evaluation

For each participant NutriFlow computes:

- baseline MealPlanFit for the original recipe and Person-specific portion;
- transformed MealPlanFit for the same Person-specific portion;
- NutritionPlan-backed rule changes and score delta;
- preference delta based on existing Person FoodPreference evidence.

A shared variant is rejected when any participant becomes ineligible or when any NutritionPlan-backed rule becomes worse. Safety and mandatory rules therefore remain Person-specific hard gates.

### Classification

A surviving variant is classified as `plan_adapted` only when at least one participant has a demonstrable improvement in persisted NutritionPlan-backed rule evidence and no participant's plan becomes worse.

A surviving variant with no NutritionPlan-backed improvement may be classified as `preference_variant` only when the Family preference result improves while no participant's preference becomes worse. This classification carries no nutritional-improvement claim.

If neither condition is met, the variant is omitted and the unchanged recipe remains the fallback.

### Ranking

Within the first slice, `plan_adapted` variants rank ahead of preference-only variants. Plan-adapted variants prefer broader participant improvement and stronger minimum/average plan-score improvement before Family preference signals. Stable operation identifiers provide deterministic final tie-breaking.

Future ranking may add pantry, cost, availability and minimal-disruption terms after the stronger safety/plan/fairness signals.

## API

The Family endpoint accepts participant-specific quantities and optional DailyNutritionState ids. The response includes baseline and transformed MealPlanFit evidence per Person and the server-calculated classification. The browser must not recreate plan authority or transformation classification.

## Consequences

- one Person's plan cannot silently override another Person's safety or mandatory guidance;
- no active NutritionPlan means no `plan_adapted` claim;
- a no-plan household can still receive neutral preference variants;
- common recipe adaptation remains compatible with Person-specific portions;
- the unchanged Family recipe is always a valid fallback when no transformation is demonstrably preferable;
- later operations such as quantity adjustment, structured side additions and optional-ingredient reduction can reuse the same shared evaluation contract.
