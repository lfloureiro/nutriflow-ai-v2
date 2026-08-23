# Calorie-aware recommendation and feedback loop

## Purpose

Meal recommendation must explain not only which option ranks highest, but how it fits each Person's daily energy budget. Recommendation feedback must remain a secondary, explainable learning signal rather than replacing deterministic nutrition and safety rules.

## Family and Person setup

Normal product setup is now:

`Create Family -> add Person -> calculate Person energy target -> plan/recommend meals`.

A Family requires a name and timezone. A Person can be created from the People screen with the minimum data needed for an adult energy estimate:

- name;
- date of birth;
- sex used specifically for the energy-calculation formula;
- height;
- weight;
- habitual activity level;
- goal: maintain, lose or gain weight;
- target kg/week when losing or gaining;
- standard-breakfast calories.

The server stores the profile, height/weight measurements, NutritionGoal and generated NutritionTarget in one transaction.

### Initial automatic energy calculation

The first implementation uses Mifflin-St Jeor for adults (18+) and explicit activity multipliers:

- sedentary: 1.20;
- light: 1.375;
- moderate: 1.55;
- active: 1.725;
- very active: 1.90.

TDEE is `BMR x activity factor`.

For weight loss/gain, the requested kg/week is converted using 7700 kcal/kg, with the adjustment capped to 20% of estimated TDEE. This cap is a product safety/robustness guard against an extreme initial target, not a clinical prescription.

The initial operational range is centered on the adjusted TDEE with a +/-100 kcal band. Formula, inputs, activity factor, goal adjustment and calculation version are persisted in `NutritionTarget.calculation_inputs` so the estimate is auditable and can be replaced by a later algorithm.

Automatic calculation currently rejects people under 18 instead of applying an adult formula silently. A dedicated child/adolescent target method is deferred.

## Daily energy budget

Each Person may have an active `NutritionTarget` with:

- estimated BMR and TDEE provenance;
- daily energy minimum and maximum;
- nutrient target components;
- validity interval and calculation version.

`DailyNutritionState` remains the operational state used by the recommendation engine. For a day it separates:

- energy already consumed;
- energy already planned but not yet consumed;
- energy explicitly assumed;
- remaining minimum and maximum energy;
- nutrient consumed/planned/remaining values.

The recommendation UI derives the original daily energy target from:

`consumed + planned + assumed + remaining`

and shows, per selected Person and day:

`Target | Consumed | Planned | Assumed | Remaining`.

Future days created through planning bootstrap use the active `NutritionTarget`, so their initial remaining range is the full daily target, less any explicit assumptions. As Servings enter the plan, recalculation reduces the remaining budget.

## Missing-breakfast assumption

A missing breakfast must not be silently treated as zero calories and must not be recorded as a meal the user never declared.

When planning/recommending at or after 10:00 local time:

1. check whether that Person has a non-cancelled/non-skipped breakfast MealEvent for the date;
2. if breakfast exists, no breakfast assumption is applied;
3. if breakfast does not exist, add the Person's `standard_breakfast_kcal` to `energy_assumed_kcal`;
4. if the Person has no configured value, use the system default of 350 kcal;
5. a configured value of 0 explicitly disables the breakfast assumption for a Person who normally skips breakfast.

Before 10:00, no breakfast assumption is applied because breakfast may still be upcoming.

Assumed calories reduce the remaining energy budget used by recommendation scoring, but they remain distinct from `energy_consumed_kcal` and `energy_planned_kcal`. Assumption metadata is stored in `DailyNutritionState.calculation_inputs`. When a real breakfast is subsequently declared, the next recalculation removes the assumption and uses the breakfast Serving nutrition instead.

This is an estimation/fallback mechanism, not evidence that food was consumed.

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

The existing energy score remains authoritative for calorie fit. Candidate energy is compared with the Person's remaining energy range after consumed, planned and explicitly assumed energy.

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

## Next calorie-planning step

The target and remaining-budget model does not yet automatically size the same recipe differently for each Person or reserve an explicit calorie share for breakfast/lunch/snack/dinner. The next planning block should therefore implement Person-specific portion sizing and meal-level calorie allocation while keeping the daily target authoritative.

## Future ML

This heuristic layer is intentionally explainable. Persisted recommendation runs, score components and feedback events provide the training data needed for a later acceptance-probability model. A future ML score should remain an additional bounded component and not bypass mandatory safety/nutrition filters.
