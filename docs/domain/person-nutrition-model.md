# Person and Nutrition Domain Model

## Purpose

This document defines the person-centric domain foundation of NutriFlow AI v2.

The objective is to model enough information to understand:

- who the person is;
- what their nutritional requirements are;
- what they want to achieve;
- what they may or may not eat;
- when they normally eat and exercise;
- what health and activity data is available;
- whether the nutrition strategy is producing the intended results.

The Person is the central subject of nutrition planning.

---

## Person

`Person` represents identity and relatively stable personal information.

Initial attributes:

- id;
- family_id;
- first_name;
- last_name;
- birth_date;
- preferred_locale;
- timezone;
- created_at;
- updated_at.

Person must not become a container for every piece of nutrition or health information.

Changing or historical values belong to dedicated entities.

---

## Personal profile

Some personal attributes are required for nutrition calculations or presentation preferences.

Candidate attributes include:

- biological sex used for energy calculations;
- preferred measurement system;
- preferred energy unit;
- preferred language;
- timezone.

Values required by a nutritional formula must be explicitly supplied or confirmed by the person.

NutriFlow must not infer biological attributes from names, appearance or unrelated data.

---

## Anthropometric measurements

Body measurements are historical observations.

Examples include:

- weight;
- height;
- body-fat percentage;
- lean mass;
- waist circumference;
- other measurements that later have a justified nutrition use case.

Each measurement records:

- person_id;
- metric;
- value;
- unit;
- measured_at;
- source;
- provider where relevant;
- external_id where relevant;
- created_at.

Example:

2026-08-21 | weight | 103.0 kg
2026-08-28 | weight | 102.4 kg
2026-09-04 | weight | 101.9 kg

NutriFlow derives the latest value and trends from this history.

---

## Nutrition goals

Goals describe intended outcomes, not measurements.

Examples:

- weight loss;
- weight maintenance;
- weight gain;
- muscle gain;
- performance support;
- medically supervised target.

A NutritionGoal can contain:

- person_id;
- goal_type;
- target_weight;
- target_rate;
- start_date;
- target_date;
- status;
- source;
- notes.

Goals must retain history.

Changing a goal should not erase previous goals.

---

## Energy and nutrition targets

Calculated nutrition targets are not permanent attributes of Person.

A NutritionTarget represents a calculation valid for a period of time.

It may contain:

- estimated BMR;
- BMR calculation method;
- estimated total energy expenditure;
- expenditure calculation method;
- target energy range;
- protein minimum/range;
- carbohydrate range;
- fat range;
- fibre target;
- other nutrient targets;
- valid_from;
- valid_until;
- calculation inputs;
- calculation version;
- source.

The calculation chain should remain explainable.

Example:

BMR
-> baseline activity estimate
-> observed activity adjustment
-> estimated TDEE
-> goal adjustment
-> recommended energy target

NutriFlow must be able to explain why a given calorie target exists.

---

## Nutrition constraints

A NutritionConstraint represents a rule that affects what can be recommended.

Examples:

- sodium maximum;
- protein minimum;
- carbohydrate range;
- ingredient exclusion;
- meal timing restriction;
- clinician-defined dietary rule.

Important attributes include:

- person_id;
- constraint_type;
- nutrient or food target;
- operator;
- value;
- unit;
- severity;
- source;
- professional provenance;
- start_date;
- end_date;
- notes.

Possible sources:

- user;
- doctor;
- nutritionist;
- system.

A mandatory professionally defined constraint must not be silently overridden by recommendation algorithms.

---

## Food preferences and adverse reactions

Preference and safety are different concepts and must remain separate.

Examples:

Preference:
"I do not like mushrooms."

Strong preference:
"I really like pasta."

Intolerance:
"Lactose causes digestive discomfort."

Allergy:
"Peanut allergy."

These distinctions affect recommendation priority.

A dislike may reduce ranking.

An allergy may completely exclude a meal.

Candidate attributes:

- person_id;
- subject type;
- subject id or normalized value;
- relation type;
- intensity;
- severity;
- source;
- notes.

---

## Schedule

Nutrition planning must understand when a person is available to eat and when shared meals are possible.

Schedule entries may describe:

- work;
- school;
- commute;
- sleep;
- training;
- habitual meal times;
- recurring family commitments;
- exceptional events.

A ScheduleEntry can contain:

- person_id;
- event_type;
- start time;
- end time;
- recurrence;
- location;
- flexibility;
- notes.

Schedules must support both recurring patterns and date-specific exceptions.

---

## Activity and training

Activity must not be represented only by a static label such as `sedentary`.

NutriFlow may initially use a baseline activity classification when insufficient data exists, but should progressively use observed activity.

Relevant information includes:

- workouts;
- workout type;
- duration;
- intensity;
- steps;
- active energy;
- resting energy;
- training frequency;
- planned workouts;
- observed activity trends.

Wearable energy estimates are signals, not exact instructions to eat back the same number of calories.

---

## Health connections

Health data connections belong to an individual Person.

A family connection does not automatically grant access to the health data of all family members.

A HealthConnection may include:

- person_id;
- provider;
- connection status;
- permissions granted;
- last successful sync;
- sync cursor;
- provider account metadata;
- created_at;
- revoked_at.

Initial provider architecture should allow:

- Apple Health / HealthKit;
- Android Health Connect;
- Garmin;
- Withings;
- Oura;
- Fitbit;
- future providers.

Provider-specific payloads must be normalized before being used by nutrition logic.

---

## Health measurements

Imported health data may include:

- body measurements;
- steps;
- workouts;
- active energy;
- resting energy;
- heart rate;
- resting heart rate;
- HRV;
- sleep;
- hydration;
- nutrition data;
- other justified wellness metrics.

Every record requires provenance sufficient to prevent duplicate counting.

Example duplicate path:

Garmin Watch
-> Garmin Connect
-> Apple Health
-> NutriFlow

and simultaneously:

Garmin API
-> NutriFlow

NutriFlow must be able to identify that these may describe the same underlying event.

---

## Daily health and nutrition state

Planning algorithms should not query thousands of raw measurements every time they need context.

NutriFlow derives a `DailyHealthState` and `DailyNutritionState`.

Possible derived fields include:

- latest weight;
- weight trend 7 days;
- weight trend 28 days;
- activity trend;
- recent training load;
- sleep duration trend;
- resting heart-rate trend;
- HRV trend;
- estimated expenditure;
- calories consumed;
- calories already planned;
- protein consumed;
- protein already planned;
- remaining energy and nutrient targets;
- adherence indicators;
- confidence level.

Derived state is recalculable from underlying data.

---

## Adaptive nutrition loop

The intended feedback loop is:

Person
-> Goal
-> Nutrition Target
-> Meal Planning
-> Actual Intake
-> Activity / Health Measurements
-> Observed Outcome
-> Recalibration
-> Next Plan

The system therefore evaluates whether the nutrition strategy is producing the expected result.

It does not simply generate a static diet.

---

## Family relationship

A Person may belong to a Family.

Family membership provides shared context such as:

- shared meals;
- pantry;
- shopping;
- recipes;
- cooking resources;
- household schedule;
- restaurants and delivery sources.

Nutrition requirements remain individual.

A shared dinner may therefore be one MealEvent with several individual Servings.

---

## Initial implementation sequence

Recommended domain sequence:

1. Person profile;
2. anthropometric measurements;
3. nutrition goals;
4. nutrition constraints;
5. food preferences and adverse reactions;
6. schedules;
7. nutrition targets;
8. health connections;
9. normalized health measurements;
10. derived DailyHealthState and DailyNutritionState.

Each stage should be designed and tested before introducing the next one.
