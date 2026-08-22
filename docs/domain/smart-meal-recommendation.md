# Smart meal recommendation

NutriFlow v2 recommendation combines the stronger deterministic nutrition and safety engine already present in v2 with the useful planning/diversity heuristics from NutriFlow v1.

## Decision order

The recommendation pipeline is deliberately layered:

1. mandatory safety and nutrition exclusions;
2. meal-type planning suitability;
3. calorie and nutrient fit against the current Person daily state;
4. personal recipe preference/rating;
5. secondary Family preference signal;
6. practical availability, location, time and source channel;
7. recent-history diversity and protein/category rotation;
8. deterministic rank and Top 3 presentation.

A diversity score never restores a candidate rejected by a mandatory rule.

## v1-inspired diversity

The v1 auto meal planner selected one slot at a time and updated its in-memory history before scoring the next slot. v2 preserves that behaviour for multi-day recommendation without copying the old score scale directly.

The `diversity-v1` component considers:

- same candidate already planned/used today;
- last use within 3, 7, 14 or 21 days;
- novelty when not recently used;
- 7-day balance between meat, fish and vegetarian/legume categories;
- repeating the previous category;
- repeating the previous primary protein;
- category repetition in recent instances of the same meal type;
- avoiding three meat meals in a row;
- repeated use of the same protein.

The weights are calibrated to the smaller v2 score scale. The large absolute v1 penalties are not copied verbatim.

## Planning profiles

`MealCandidatePlanningProfile` keeps recommendation/planning metadata separate from nutrition catalogue identity and works for both Recipes and commercial FoodItems.

It can define:

- `planning_category`;
- `primary_protein`;
- `suitable_meal_types`;
- `auto_plan_enabled`.

Explicit profiles win. Candidates without a profile use conservative name/ingredient inference as a fallback so newly created recipes can still participate before being curated.

## Multi-day recommendation

The web planner requests dates sequentially rather than in parallel.

For each date:

1. backend scores all eligible candidates;
2. only the Top 3 are returned to the normal UI;
3. rank 1 is treated as the provisional choice for planning the next requested date;
4. that provisional history is sent with the next request;
5. the next date therefore penalizes immediate repetition and improves category/protein rotation.

The provisional selection is not persisted as a MealEvent until the user explicitly adds it to the plan.

## Explainability and provenance

The persisted recommendation still keeps the full evaluation set. The normal UI receives only the requested Top N, while score breakdown and explanations retain components such as:

- `energy`;
- `nutrients`;
- `preferences`;
- `family_preferences`;
- `advisory_reactions`;
- `diversity`.

Recommendation context persists the provisional history used for the run.

## Machine learning

NutriFlow v1 optionally blended the heuristic score with a model predicting Family acceptance. v2 deliberately does not import the old trained model. Recommendation runs, alternatives and accepted/rejected decisions are already persisted, allowing a future v2-native acceptance model to be trained on compatible feedback. The explainable heuristic remains authoritative until there is sufficient v2 evidence to justify that layer.
