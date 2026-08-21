# NutriFlow AI v2 — Product Vision

## Purpose

NutriFlow AI v2 is a standalone person-centric adaptive nutrition platform for individuals and families.

The central question is no longer only "what should we eat this week?". The product should answer:

> Given who each person is, their goals, health and nutrition constraints, schedules, activity, shared family meals, available food and observed results, what is the best practical nutrition plan for this person and this family now?

## Core product model

The primary entity is the **Person**. A Person may belong to a **Family**. The Family provides shared context, but nutrition requirements and outcomes remain individual.

The conceptual flow is:

`Person -> Family -> Health -> Schedule -> Meal Events -> Servings -> Nutrition State -> Outcomes -> Feedback`

### Person

Each person can have:

- identity and demographic information required for nutrition calculations;
- height, weight and body-composition history;
- activity level and training schedule;
- energy and macro targets;
- dietary preferences and dislikes;
- allergies and intolerances;
- doctor- or nutritionist-defined constraints;
- goals such as weight loss, maintenance, muscle gain or performance;
- personal schedule and usual meal times;
- health-data connections;
- personal language, units and display preferences.

Calculated values such as calorie targets must retain their derivation rather than only storing a final number. For example:

`BMR -> activity estimate -> TDEE -> goal adjustment -> target range`

This allows targets to be recalculated as the person's weight, activity or goals change.

## Family context

A Family represents the shared environment around its members, including:

- family membership;
- shared meal opportunities;
- household pantry and inventory;
- recipes;
- shopping lists;
- cooking equipment;
- restaurants and delivery sources;
- shared preferences where appropriate;
- meal history.

A family meal is a shared Meal Event, not a requirement for every participant to eat the same quantity.

## Meal Events and servings

Planning is based on **Meal Events**.

A Meal Event describes:

- date and time;
- meal type;
- participants;
- location;
- source (home cooked, restaurant, delivery, leftovers, etc.);
- recipe or food items;
- planned and actual servings.

Every participant can have an individual **Serving**. A single family recipe may therefore generate different portions and nutritional values for each person.

This enables the system to select one practical family dinner while adapting portion size and composition to each participant's remaining nutritional needs.

## Daily nutrition state

NutriFlow should maintain a per-person Daily Nutrition State containing, where available:

- daily energy target/range;
- calories consumed;
- calories planned but not yet consumed;
- calories remaining;
- macro and key nutrient targets;
- actual and planned nutrient totals;
- activity context;
- training context;
- adherence and confidence information.

The planner can therefore optimise the whole day rather than scoring each meal in isolation.

## Adaptive nutrition

NutriFlow AI v2 should combine:

- deterministic safety and nutrition rules;
- heuristics;
- personal preferences;
- family constraints;
- observed behaviour;
- health and activity data;
- machine-learning ranking where appropriate.

The system should gradually learn an individual's observed energy balance using intake, weight trends and activity rather than relying forever on a static TDEE formula.

It must not naively treat every calorie reported by a wearable as an exact number of calories that should be eaten back.

## Health Data Hub

Health data is connected per Person, never globally per Family.

Possible providers include:

- Apple Health / HealthKit;
- Android Health Connect;
- Garmin;
- Withings;
- Oura;
- Fitbit;
- future providers.

Internally, provider-specific data should be normalised into a common model with provenance, timestamps, source device/provider and quality/confidence metadata.

The platform must handle duplicate data paths such as a Garmin activity entering through both Garmin and Apple Health.

Useful data may include:

- weight and body composition;
- activity and steps;
- workouts;
- active/resting energy;
- heart-rate context;
- sleep;
- nutrition and hydration records;
- other wellness metrics when they have a justified nutrition use case.

## Outcome feedback loop

The long-term product loop is:

`Plan -> Eat -> Observe -> Evaluate -> Recalibrate -> Plan`

Examples of observed outcomes include:

- weight trend;
- body-composition trend;
- adherence;
- activity/training changes;
- sleep/recovery context;
- meal acceptance/rejection/modification;
- portion changes;
- restaurant/delivery substitutions.

The system should detect when observed results materially differ from the intended goal and surface that difference rather than blindly making aggressive automatic changes.

## Professional supervision

A Person may be self-managed or professionally supervised.

Professional guidance can introduce explicit constraints such as:

- energy target/range;
- protein minimum;
- sodium maximum;
- carbohydrate range;
- fibre minimum;
- exclusions;
- meal timing;
- weight goal and target rate.

Constraints need provenance (`user`, `doctor`, `nutritionist`, `system`) and priority/severity. Mandatory clinician-provided rules must not be silently overridden by recommendation algorithms.

## Wellness boundary

Initial NutriFlow positioning is wellness and nutrition planning, not autonomous diagnosis or treatment.

The platform may apply medical or dietetic constraints provided by the user or a professional, but should not infer a disease and prescribe treatment as though acting as a clinician.

This boundary must be reviewed whenever new clinical features are proposed.

## Platform requirements from day one

These are architectural requirements, not future polish:

- multilingual/i18n;
- per-user locale and units;
- Light, Dark and System appearance modes;
- design tokens rather than hard-coded colours;
- responsive desktop, tablet and mobile layouts;
- web-first UI with a path to native mobile integrations;
- accessibility-aware components;
- timezone-aware scheduling;
- health-provider abstraction;
- privacy and consent controls by person and data type.

## Product success

NutriFlow AI v2 succeeds if it can make nutrition planning more practical while respecting the reality that people:

- live in families;
- eat some meals alone and others together;
- have different energy and health requirements;
- have changing schedules and activity;
- sometimes cook, sometimes use leftovers and sometimes order food;
- need recommendations that adapt to observed results rather than remain static.

The product should reduce planning effort while increasing the quality, personal relevance and explainability of nutrition decisions.

