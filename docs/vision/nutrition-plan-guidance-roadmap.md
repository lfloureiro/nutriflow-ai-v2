# NutriFlow AI v2 — Nutrition Plan & Guidance Roadmap

## Purpose

The next major NutriFlow AI v2 evolution is to turn a coherent nutrition plan into practical food decisions.

The system should be able to receive a plan from a nutritionist, clinician or user, preserve its provenance, compile it into structured rules and then use those rules to:

- evaluate existing meals;
- adapt existing recipes;
- suggest new meals to cook;
- choose among pantry/home options;
- rank restaurant and delivery meals;
- guide a weekly meal plan;
- learn from real acceptance and outcomes without overriding mandatory professional guidance.

The product goal is not a rigid static menu. It is an adaptive guidance layer over the meal-planning and recommendation foundation that already exists.

## Product principle

Keep **nutrition plan** separate from **meal plan**.

```text
Nutrition Plan
= goals, targets, constraints, guidelines, frequencies and professional/user intent

Meal Plan
= concrete breakfast/lunch/snack/dinner events scheduled for actual days
```

The Nutrition Plan guides the Meal Plan; it does not replace it.

## Existing foundation to reuse

Do not build a parallel nutrition system. Reuse the current domain wherever semantics match:

- `Person` and `Family`;
- `NutritionGoal`;
- `NutritionTarget` and target components;
- `NutritionConstraint` with provenance, severity and mandatory semantics;
- `DailyNutritionState`;
- `FoodItem` and versioned `FoodCompositionSnapshot`;
- `Recipe` and versioned `RecipeCompositionSnapshot`;
- `MealEvent`, `MealParticipant` and Person-specific `Serving`;
- `MealCandidateAvailability`;
- `MealCommercialOffer`;
- recommendation ranking, preference, history and feedback;
- pantry and shopping;
- external menu ingestion.

The central design task is to add the missing coherent plan layer and compilation/evaluation logic.

## Target architecture

```text
                     original plan text/document
                               |
                               v
                        NutritionPlan
                               |
             +-----------------+------------------+
             |                 |                  |
             v                 v                  v
      constraints/limits     targets          guidelines
             |                 |                  |
             +-----------------+------------------+
                               |
                               v
                    EffectiveNutritionPlan
                Person + date + meal + context
                               |
                +--------------+--------------+
                |              |              |
                v              v              v
             Recipe        Home/Pantry   External meal
                |              |          Restaurant/Delivery
                +--------------+--------------+
                               |
                               v
                      Meal Plan-Fit evaluation
                               |
                  +------------+------------+
                  |                         |
                  v                         v
            recommend as-is          transformation proposal
                                              |
                                              v
                                     recalculate + rescore
```

## Domain model direction

### NutritionPlan

A first-class `NutritionPlan` should represent a coherent plan rather than a loose collection of unrelated constraints.

Minimum fields/concepts:

```text
NutritionPlan
    id
    person_id
    title
    source_type
    source_name
    source_reference
    original_text / document reference
    version
    status
    valid_from
    valid_until
    created_at / updated_at
```

Possible `source_type` values should support at least:

```text
nutritionist
clinician
user
system
imported
```

Professional source and NutriFlow-derived guidance must never be conflated.

### Plan rule categories

A plan may contain several semantic classes of instruction.

#### Mandatory constraint

Examples:

```text
sodium <= 2000 mg/day
exclude allergen X
protein >= 50 g at lunch
```

Use or associate with existing `NutritionConstraint` where semantics match.

#### Numeric target or range

Examples:

```text
protein 45-55 g at lunch
fibre >= 10 g at dinner
energy 500-650 kcal at lunch
```

Reuse `NutritionTarget` semantics where practical, but support meal-context applicability.

#### Qualitative guideline

Examples:

```text
prefer salad/vegetables at lunch
prefer unsaturated fats
reduce ultraprocessed foods
choose lean protein where practical
```

These are not naturally hard constraints and must not be forced into numeric constraint fields.

#### Weekly frequency guideline

Examples:

```text
fish >= 3 meals/week
legumes >= 3 meals/week
red meat <= 2 meals/week
```

Frequency guidance requires period-aware evaluation and later weekly planner integration.

## Rule metadata

Every plan rule/guideline should preserve enough metadata to answer:

- who authored it;
- whether it is mandatory or advisory;
- what Person it applies to;
- what meal types it applies to;
- whether it is daily, per-meal or weekly;
- date validity;
- original source reference;
- confidence/confirmation state where the rule was parsed from free text;
- whether it was prescribed, user-entered or derived by NutriFlow.

Do not silently promote an AI-parsed interpretation to a mandatory rule.

## Phase 1 — Nutrition Plan foundation

### Goal

Represent coherent plans with provenance and structured rules without yet building AI parsing or meal transformation.

### Deliverables

- `NutritionPlan` model;
- plan version/lifecycle semantics;
- plan-to-rule associations;
- representation for qualitative/frequency guidelines;
- meal-type applicability;
- source/provenance semantics;
- API CRUD/read models needed for later UI;
- migration;
- tests;
- ADR/domain documentation.

### Key design rule

Reuse existing `NutritionConstraint`, `NutritionTarget` and `NutritionGoal` when they correctly represent the concept. Do not duplicate them merely to make all data live under one table.

## Phase 2 — EffectiveNutritionPlan compiler

### Goal

Produce one deterministic server-authoritative object describing what matters for a Person at a specific meal instant.

Conceptual service:

```python
get_effective_nutrition_plan(
    person_id,
    scheduled_at,
    meal_type,
    context,
)
```

The compiler combines, with explicit precedence/provenance:

```text
active professional plan
+ active user plan/guidance
+ mandatory NutritionConstraint
+ current NutritionTarget
+ NutritionGoal
+ DailyNutritionState
+ meal context
+ weekly-frequency progress where applicable
```

Example output concept:

```text
Lunch / Person X

Mandatory
- sodium maximum ...

Targets
- protein 45-55 g
- vegetables >= 250 g equivalent guideline/measure when evidence exists
- fibre >= 10 g

Guidelines
- prefer salad/vegetables
- favour unsaturated fat

Current-day context
- energy remaining ...
- protein remaining ...

Weekly context
- fish meals completed 1/3
```

### Requirements

- deterministic;
- explainable;
- provenance-preserving;
- no browser-authored calculations;
- no invented missing evidence;
- conflicting rules surfaced explicitly rather than silently discarded.

## Phase 3 — Plan import and parser

### Goal

Allow a user to paste or upload a nutrition plan and convert it into proposed structured rules.

Supported input direction:

- pasted text;
- manually entered plan;
- later PDF/document/photo ingestion.

Parser flow:

```text
source document/text
-> extract proposed plan statements
-> normalize candidate rules
-> show source statement + interpretation
-> user confirmation/edit
-> activate confirmed rules
```

### Safety/product rule

Always distinguish:

```text
PRESCRIBED / SOURCE PLAN
```

from:

```text
NUTRIFLOW SUGGESTION / DERIVATION
```

A parsed interpretation must remain reviewable and must not silently become a clinician-authored statement.

## Phase 4 — Meal Plan-Fit evaluation

### Goal

Evaluate any normalized meal candidate against an EffectiveNutritionPlan.

Conceptual output:

```text
MealPlanFit
    overall_score
    hard_rule_status
    component_scores
    gaps
    strengths
    missing_evidence
    explanations
```

Example:

```text
Protein       32 / 50 g     below target
Vegetables   target met
Fibre          7 / 10 g     below target
Saturated fat acceptable
Meal guideline matched

Plan Fit: 76%
```

The score is secondary to the explanation. Hard-rule failure remains an exclusion, not something an average score can hide.

### Same evaluator for every source

Do not implement separate nutrition-fit engines for:

- home recipes;
- leftovers;
- pantry combinations;
- restaurant dishes;
- Uber Eats;
- Glovo;
- future providers.

All candidates must be normalized into existing FoodItem/Recipe/composition evidence and then evaluated by one common engine.

## Phase 5 — Meal Transformation

### Goal

Adapt a familiar meal rather than only reject it.

Structured transformation actions should include at least:

```text
ADD
REMOVE
INCREASE
REDUCE
SWAP
CHANGE_PORTION
CHANGE_COOKING_METHOD
```

Example:

```text
Chicken 120 g -> 180 g
ADD chickpeas 60 g
REDUCE creamy dressing 30 g -> 10 g
```

Then:

```text
original meal
-> proposed transformation
-> recalculate nutrition
-> re-run hard rules
-> re-run Plan-Fit
-> compare before/after
```

### Important persistence rule

Do not destructively modify the original Recipe merely because the engine proposes an adaptation.

A transformation starts as a proposal/derived meal option. The user may later choose to save it as a new recipe variant.

## Phase 6 — Home, pantry and recipe guidance

### Goal

Use the plan to answer practical questions such as:

```text
What can I eat for lunch now?
What can I make with what is at home?
How can I adapt tonight's planned meal?
```

Rank across:

- existing recipes;
- pantry-available recipes;
- leftovers/history candidates where represented;
- transformed variants;
- new recipe suggestions once composition can be calculated safely.

Practical scoring continues to include preparation time, kitchen availability, schedule and household constraints.

## Phase 7 — Restaurant and delivery guidance

### Goal

Use exactly the same plan-fit logic on external commercial food.

Pipeline:

```text
Person + effective plan
-> time/location/provider context
-> restaurant/delivery discovery
-> external menu normalization
-> nutrition evidence classification
-> mandatory-rule evaluation
-> Plan-Fit
-> preferences/history
-> practical factors (price/time/availability)
-> Top recommendations
```

External nutrition may be incomplete. Confidence/evidence level must remain visible. Missing evidence must not be treated as zero.

### Provider strategy

Provider adapters are replaceable inputs, not product logic.

Current reality:

- Uber consumer access may require explicit/early access approval;
- public Glovo APIs do not currently expose a general consumer marketplace discovery contract;
- public Bolt Food integration is merchant/POS-oriented.

Therefore NutriFlow must support provider adapters, restaurant discovery, imported/observed menus and future sources without coupling the nutrition engine to any one provider.

## Phase 8 — Adaptive weekly planning

### Goal

Use the same effective-plan and meal-fit engine to produce a coherent week rather than independent meal suggestions.

Optimise jointly for:

- mandatory plan rules;
- daily nutrient targets;
- weekly frequency targets;
- preferences;
- recent meal history;
- category/protein diversity;
- Family shared meals;
- Person-specific portions;
- pantry;
- shopping requirements;
- schedule/time constraints;
- restaurant/delivery use where appropriate.

Reuse the existing repeat penalties, diversity signals and meal-suitability profiles.

## Phase 9 — Feedback and learning

### Goal

Improve ranking from observed behaviour while preserving safety and professional intent.

Useful feedback includes:

```text
ate as suggested
ate less/more
modified meal
rejected recommendation
liked/disliked
ordered something else
saved transformation
```

Learning can influence preference and practical ranking, but must never weaken mandatory adverse-reaction or professional constraint handling.

## Parallel track — Trustworthy catalogue enrichment

This is an enabling track, not a competing product direction.

Plan-Fit and Meal Transformation are only as credible as the underlying nutrition evidence.

Continue to improve:

- authoritative generic-food nutrition sources;
- ingredient matching/review;
- source/version provenance;
- safe unit/reference normalization;
- recipe recalculation from enriched ingredients;
- evidence-class distinction between curated, imported, user-entered and synthetic development data.

Do not delay the NutritionPlan domain until the catalogue is perfect, but do not overstate precision when evidence is incomplete.

## Frontend direction

Keep the existing lightweight progressive-disclosure model.

Do not add a new top-level Family menu for Nutrition Plan.

Recommended Person navigation:

```text
Pessoas
  -> Person
      -> Nutrição
          -> Visão geral
          -> Plano
          -> Objetivos
          -> Restrições
          -> Histórico
```

`Plano` should show a compact active-plan summary first, then drill into:

- source/professional;
- validity;
- meal-specific targets;
- guidelines;
- weekly frequencies;
- restrictions;
- original source/document;
- adherence/coverage later.

The meal-operational surfaces remain:

```text
Refeições -> Hoje | Semana | Recomendar
```

## Recommended development sequence

The implementation sequence should be treated as authoritative unless a concrete blocker justifies reordering:

```text
Phase 1  NutritionPlan domain
Phase 2  EffectiveNutritionPlan compiler
Phase 3  plan import/parser + confirmation
Phase 4  Meal Plan-Fit
Phase 5  Meal Transformation
Phase 6  home/pantry guidance
Phase 7  restaurant/delivery guidance
Phase 8  adaptive weekly planning
Phase 9  feedback/learning refinement
```

Do not jump directly to a Glovo/Uber-specific UI before Phases 1-5 are stable; otherwise provider integration would be built without the core nutrition-guidance semantics it is meant to serve.

## Immediate next branch

Start from verified `main` with:

```text
feature/nutrition-plan-guidance-foundation
```

The first branch should cover Phase 1 and the minimum deterministic compiler foundation from Phase 2 only.

### First-branch acceptance criteria

- migration applies cleanly;
- existing plan/meal/recommendation history remains intact;
- a Person can own/version/activate/deactivate NutritionPlans;
- source/professional provenance is preserved;
- rules can be scoped by validity and meal type;
- numeric constraints/targets reuse existing models where semantically correct;
- qualitative/frequency guidelines have a proper representation;
- EffectiveNutritionPlan can deterministically resolve the active rule set for a Person/date/meal;
- mandatory/advisory priority is explicit;
- conflicts and missing evidence are surfaced;
- no AI parser is required to create/test a plan manually;
- no external meal provider dependency is introduced;
- tests, docs and ADR are included;
- all standard local/CI gates pass with zero warnings.
