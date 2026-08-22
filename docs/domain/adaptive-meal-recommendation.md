# Adaptive meal recommendation foundation

## Purpose

This increment introduces the first deterministic recommendation layer for NutriFlow.

The recommendation engine ranks candidate foods and recipes for one Person using the current `DailyNutritionState`, active preferences, adverse reactions and nutrition constraints.

It does not create a MealEvent automatically and it does not use machine learning yet.

The boundary is intentional: recommendation is a decision step. Acceptance, modification and persistence as a planned meal are separate actions.

## Layering

The engine follows the architecture rule that non-negotiable constraints are evaluated before ranking:

```text
candidate catalogue item
-> mandatory adverse-reaction checks
-> mandatory nutrition constraints
-> nutrition fit
-> preference/advisory scoring
-> deterministic ranking
```

An excluded candidate never receives a ranking score that could allow it to re-enter through heuristics or future ML.

## Candidate construction

Candidates are built from an explicit versioned composition snapshot:

- `FoodCompositionSnapshot` for a FoodItem;
- `RecipeCompositionSnapshot` for a Recipe.

The caller supplies a proposed quantity and quantity unit.

The existing safe composition-scaling logic produces the candidate's energy and nutrient snapshot. This means recommendation and eventual Serving calculation use the same quantity-conversion semantics.

Recipe candidates expose both the recipe key and the subject keys of their FoodItem ingredients. This allows an ingredient allergy or exclusion to remove a recipe before ranking.

## Hard safety rules

### Mandatory adverse reactions

An active mandatory `FoodAdverseReaction` excludes a candidate when its subject type/key is present in the candidate.

This applies to direct FoodItem candidates and to ingredients inside Recipe candidates.

### Mandatory food exclusions

Active mandatory `NutritionConstraint` records with `operator = exclude` are evaluated against supported food/ingredient/product/recipe subject types.

### Mandatory nutrient maxima

Active mandatory nutrient constraints using `max`, `lte` or `<=` are evaluated against:

- nutrition already consumed today;
- nutrition already planned today;
- the candidate's proposed nutrient contribution.

If the total would exceed the mandatory maximum, the candidate is excluded.

A mandatory nutrient maximum is also a data-completeness requirement for that candidate. If the selected candidate composition does not contain a value for the constrained nutrient, the engine cannot prove that the candidate is within the mandatory maximum. The candidate therefore fails closed with:

```text
mandatory_nutrient_data_missing:<nutrient_key>
```

Missing data is distinct from an explicitly measured value of zero. A present nutrient component with value `0` remains valid evidence and is evaluated normally.

This exclusion is candidate-scoped: one candidate with incomplete mandatory nutrient data does not stop other candidates with sufficient data from being evaluated.

### Unsupported mandatory constraints

The engine fails closed.

If an active mandatory constraint cannot yet be evaluated safely, recommendation stops with `UnsupportedMandatoryConstraintError` rather than silently ignoring the rule.

This is a deliberate safety boundary.

## Unit conversion

Nutrition comparisons only use explicit safe conversions already supported by serving-nutrition calculation:

- mg <-> g <-> kg;
- ml <-> l;
- identical units.

Mass-to-volume conversion is not inferred. Density assumptions require explicit future modelling.

If an unsupported conversion is required to evaluate a mandatory constraint, the recommendation run stops rather than guessing.

## Ranking

Eligible candidates receive an explainable deterministic score composed of:

- energy fit against the current remaining daily energy range;
- contribution toward outstanding nutrient minimums;
- penalty for exceeding remaining nutrient maxima;
- active user likes/dislikes;
- advisory adverse-reaction penalties.

The score breakdown is returned with each candidate.

The exact scoring semantics are versioned by `engine_version`, initially `meal-recommendation-v1`.

The score is a ranking heuristic, not a clinical judgement.

## Explainability

Each evaluation exposes:

- eligibility;
- rank when eligible;
- total score;
- score breakdown;
- exclusion reasons;
- positive/negative explanation signals.

Examples:

```text
supports_deficit:protein
preferred:ingredient:food:chicken
candidate_fits_remaining_energy
```

or:

```text
mandatory_reaction:ingredient:food:peanut
mandatory_nutrient_data_missing:sodium
```

This information will later support UI explanations, user feedback and ML training without making ML responsible for hard safety decisions.

## Current limitations

This first recommendation layer is intentionally person-scoped and candidate-scoped.

It does not yet:

- optimize one shared family meal across multiple Persons;
- choose candidate quantities automatically;
- resolve schedule windows or cooking-time constraints;
- persist recommendation runs/accept-reject feedback;
- create MealEvents from accepted recommendations;
- use pantry availability, restaurant/delivery availability or cost;
- use ML ranking.

These are subsequent increments built on the same hard-rule-first boundary.

## Next steps

Recommended sequence after this foundation:

1. persist recommendation decisions and accept/reject/modify feedback;
2. convert accepted recommendations into planned MealEvent/Serving records;
3. add schedule and practical-context filtering;
4. support multi-person shared-meal optimization;
5. incorporate pantry, restaurant/delivery and cost context;
6. add learned ranking only after deterministic safety and nutrition layers.
