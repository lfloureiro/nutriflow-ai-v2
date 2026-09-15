# ADR-035: Nutrition Plan as a versioned guidance envelope

- Status: Accepted
- Date: 2026-09-15

## Context

NutriFlow already has Person-level goals, versioned nutrition targets, numeric/food constraints and a mature
meal/recommendation foundation. What is missing is a coherent representation of a nutritionist-, clinician-
or user-authored plan that can explain why those rules belong together and when they apply.

Creating a second set of plan-specific nutrient limits would duplicate semantics and eventually produce two
competing nutrition engines. Treating a plan as free text only would preserve the document but would not make
its guidance usable by deterministic recommendation and future Meal Plan-Fit.

The model must also preserve professional provenance. Once an active plan has influenced decisions, editing it
in place would make historical explanations unreliable.

## Decision

1. Introduce `NutritionPlan` as a Person-scoped, versioned provenance/lifecycle envelope.
2. Use `lineage_id + version` to identify successive versions and `supersedes_plan_id` to preserve lineage.
3. Make plan content editable only in `draft`. Active/inactive/superseded content is immutable; substantive
   changes require a new version.
4. Reuse `NutritionConstraint`, `NutritionTargetComponent` and `NutritionGoal` through typed
   `NutritionPlanRule` bindings. Do not duplicate their numeric semantics in the plan tables.
5. Store qualitative and weekly-frequency instructions in `NutritionPlanGuideline`, because forcing these into
   numeric constraints would misrepresent their meaning.
6. Preserve meal-type scope, validity, source statement, confirmation state and mandatory/advisory intent.
7. Compile one deterministic `EffectiveNutritionPlan` for Person + date + meal type on the server.
8. Return all applicable rules with provenance. Priority establishes stable ordering but never silently deletes
   conflicting guidance.
9. Detect directly incompatible numeric ranges and surface them as explicit conflicts.
10. Keep AI parsing outside this foundation. Future parsed statements enter as proposed interpretations and
    require confirmation before becoming effective guidance.

## Consequences

### Positive

- professional and user plans can coexist without losing provenance;
- the existing constraint/target/goal semantics remain authoritative;
- meal-specific guidance can be expressed without modifying global numeric models;
- active plan history cannot be rewritten accidentally;
- later home, restaurant and delivery candidates can all consume the same effective-plan contract;
- parser uncertainty has a natural confirmation boundary.

### Costs

- a plan rule binding adds one level of indirection around existing objects;
- Person consistency across a binding and its referenced object is enforced in the service layer because SQL
  foreign keys cannot express cross-table Person equality directly;
- weekly frequency progress is represented but not yet calculated in this ADR's implementation block;
- Meal Plan-Fit still needs a separate evidence-aware evaluator.

## Rejected alternatives

### Duplicate plan-specific nutrient rule tables

Rejected because they would create competing semantics for constraints and targets.

### Store the plan only as text/JSON

Rejected because deterministic evaluation, provenance and relational integrity would be weak and difficult to
query or explain.

### Mutate an active plan in place

Rejected because recommendation history would no longer be explainable against the source plan that existed at
the time.

### Let the parser directly activate inferred rules

Rejected because an AI interpretation must not silently become clinician- or nutritionist-authored guidance.
