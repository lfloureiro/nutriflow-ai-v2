# Recommendation feedback model

## Purpose

NutriFlow must preserve not only the meal that was eventually chosen, but also the recommendation context that led to the choice.

The feedback domain records:

- what recommendation run was produced for a Person;
- which candidates were eligible or excluded;
- the rank, score and explanation shown for each candidate;
- the nutrition values used at that moment;
- whether an eligible option was accepted, rejected or modified;
- which Serving resulted from an accepted/modified option when one already exists.

The model is:

```text
Person
  -> MealRecommendationRun
       -> MealRecommendationOption
            -> MealRecommendationFeedback[]
                 -> optional resulting Serving
```

## MealRecommendationRun

One run represents one execution of the recommendation engine for one Person and planning date.

It stores:

- `person_id`;
- optional `daily_nutrition_state_id`;
- `planning_date`;
- optional `meal_type`;
- `engine_version`;
- optional JSON context;
- timestamps.

The DailyNutritionState reference is `ON DELETE SET NULL` because derived state can be rebuilt or cleaned up. Recommendation history remains useful even if that derived snapshot disappears.

## MealRecommendationOption

Every candidate evaluation is persisted, including candidates excluded by mandatory rules.

Stored values include:

- stable candidate key/name/kind;
- quantity and quantity unit;
- optional FoodItem or Recipe reference;
- optional exact Food/Recipe composition-snapshot reference;
- eligibility;
- rank and score for eligible options;
- score breakdown;
- exclusion reasons;
- explanation reasons;
- candidate subjects used by safety/preference matching;
- a nutrition snapshot containing energy and nutrients used for evaluation.

Eligible options must have a positive rank and score. Excluded options have neither rank nor score.

### Historical stability

Catalogue foreign keys are traceability links, not the sole historical record.

The candidate identity, quantity and nutrition snapshot are copied into the option so later catalogue changes or deletion cannot silently rewrite what NutriFlow recommended.

Decimal values stored inside JSON snapshots are represented as strings to preserve exact decimal semantics rather than passing through binary floating point.

## MealRecommendationFeedback

Feedback is an append-only event associated with an eligible recommendation option.

Supported actions are:

- `accepted`;
- `rejected`;
- `modified`.

Each event stores:

- recommendation option;
- action;
- source;
- optional metadata;
- optional resulting Serving;
- recorded timestamp plus normal entity timestamps.

A rejected event cannot reference a resulting Serving.

Accepted or modified feedback may reference a Serving when the plan has already been materialized. The Serving must belong to the same Person as the recommendation run.

## Why feedback is append-only

A person can change a choice.

Example:

```text
18:00 accepted chicken bowl
18:05 modified portion from 300 g to 250 g
```

Overwriting the first action would lose useful behaviour history. Keeping both events supports later analysis of recommendation acceptance, modifications and adherence.

## Relationship to learning

The feedback records are future learning signals, not safety rules.

Conceptually:

```text
mandatory safety / professional rules
        ↓
mandatory nutrition eligibility
        ↓
deterministic recommendation ranking
        ↓
optional learned ranking adjustment
        ↓
recommendation shown
        ↓
accepted / rejected / modified feedback
```

Future ML may use feedback to adjust ranking among already-eligible candidates. It must never bypass mandatory exclusion logic.

## Relationship to MealEvent and Serving

This increment stores recommendation history and feedback only.

A subsequent application-service increment should turn an accepted or modified recommendation into authoritative planned meal records:

```text
MealRecommendationOption
       + feedback
          ↓
MealEvent / MealParticipant / Serving
          ↓
DailyNutritionState recalculation
```

Linking feedback to a resulting Serving lets the system compare recommendation intent with later served/consumed amounts.

## Privacy

Recommendation runs and feedback are Person-scoped nutrition data. Family membership does not imply unrestricted access to another Person's recommendation history.
