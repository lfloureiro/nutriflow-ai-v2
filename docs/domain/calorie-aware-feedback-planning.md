# Calorie-aware recommendation and feedback loop

## Purpose

Meal recommendation must explain not only which option ranks highest, but how it fits each Person's daily energy budget. Recommendation feedback must remain a secondary, explainable learning signal rather than replacing deterministic nutrition and safety rules.

## Daily energy budget

Each Person may have an active `NutritionTarget` with:

- estimated BMR and TDEE provenance;
- daily energy minimum and maximum;
- nutrient target components;
- validity interval and calculation version.

`DailyNutritionState` remains the operational state used by the recommendation engine. For a day it separates:

- energy already consumed;
- energy already planned but not yet consumed;
- remaining minimum and maximum energy;
- nutrient consumed/planned/remaining values.

The recommendation UI derives the original daily energy target from:

`consumed + planned + remaining`

and shows, per selected Person and day:

`Target | Consumed | Planned | Remaining`.

Future days created through planning bootstrap use the active `NutritionTarget`, so their initial remaining range is the full daily target. As Servings enter the plan, recalculation reduces the remaining budget.

## Development demo

The development seed persists four synthetic NutritionTargets. These values are development-only and explicitly carry demo provenance.

| Person | BMR | TDEE | Daily target | Current consumed | Current planned |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pessoa Demo | 1850 | 2220 | 1800–2000 kcal | 1000 | 0 |
| Marta Demo | 1380 | 1800 | 1700–1900 kcal | 850 | 450 |
| Rui Demo | 1750 | 2400 | 2200–2400 kcal | 1200 | 600 |
| Inês Demo | 1320 | 1750 | 1600–1800 kcal | 700 | 0 |

The seed also defines protein, fibre and sodium target components and repairs previously-created future demo states that did not yet reference a target.

## Recommendation ordering

The existing energy score remains authoritative for calorie fit. Candidate energy is compared with the Person's remaining energy range after consumed and planned Servings.

The scoring pipeline is conceptually:

1. mandatory safety and nutrition exclusions;
2. energy and nutrient fit;
3. explicit Person and Family preferences;
4. practical availability/context;
5. diversity and recent meal history;
6. historical recommendation feedback.

A later signal must never restore an option excluded by an earlier mandatory rule.

## Feedback learning v1

Existing `MealRecommendationFeedback` events are reused; no new persistence model is required.

For each Person and candidate, the latest feedback event for each recommendation option is considered over a 180-day lookback:

- accepted: positive signal;
- modified: small positive signal;
- rejected: negative signal.

The signal decays with age and is clamped to a bounded range. It is stored separately in `score_breakdown` as `feedback_history` and only changes ranking when there is actual historical evidence for that candidate.

For shared-family recommendations, each participant's own feedback adjusts that participant's score before the existing minimum-score / average-score fairness ordering is recomputed.

## Future ML

This heuristic layer is intentionally explainable. Persisted recommendation runs, score components and feedback events provide the training data needed for a later acceptance-probability model. A future ML score should remain an additional bounded component and not bypass mandatory safety/nutrition filters.
