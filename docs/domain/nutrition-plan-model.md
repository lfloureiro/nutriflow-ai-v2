# Nutrition Plan domain model

## Purpose

`NutritionPlan` is the coherent guidance layer between Person-level nutrition evidence and concrete Meal Plans.
It does not replace `NutritionGoal`, `NutritionTarget`, `NutritionConstraint`, recipes, servings or meal events.
Instead, it groups reusable rules with explicit provenance, validity, meal scope and lifecycle.

## Core distinction

```text
NutritionPlan
= goals, numeric rules, qualitative guidance, frequency guidance and source intent

MealPlan
= concrete breakfast/lunch/snack/dinner events on actual dates
```

A Nutrition Plan guides meal planning and recommendation. It is not itself a schedule of meals.

## NutritionPlan

A plan is Person-scoped and contains:

- a stable `lineage_id` shared by all versions of the same plan;
- a positive `version` within that lineage;
- optional `supersedes_plan_id` provenance;
- title and source metadata;
- the original source text/reference when available;
- lifecycle status: `draft`, `active`, `inactive`, `superseded`;
- `valid_from` / `valid_until`.

Supported source categories are initially:

```text
nutritionist
clinician
user
system
imported
```

`source_type` identifies the authority/origin represented by the plan. Import mechanics must not silently
turn NutriFlow-derived text into professional guidance.

## Version and immutability semantics

Plan content is mutable only while the plan is `draft`.

Once activated, substantive changes require a new version in the same lineage. Creating a new version clones
its rule bindings and guidelines so the new draft can be reviewed without changing the active version.
Activating the replacement marks the previously active version in that lineage as `superseded` and, when the
new version starts later, closes the older version's validity immediately before the new `valid_from` date.

This preserves historical provenance and prevents an active professional plan from being rewritten in place.

Only draft plans can be physically deleted. Active plans are deactivated or superseded instead.

## Reusing existing numeric and goal models

`NutritionPlanRule` is a typed binding, not a second nutrition-rule implementation. A binding points to exactly
one existing object:

- `NutritionConstraint`;
- `NutritionTargetComponent`;
- `NutritionGoal`.

The binding adds plan-specific context that those reusable objects do not carry:

- meal type (`breakfast`, `lunch`, `snack`, `dinner`, or all meals);
- local priority;
- optional narrower validity;
- original source statement;
- whether the referenced rule also applies independently outside the plan.

By default, a rule bound into a plan is `plan_only`: its Person-level object is not separately emitted by the
effective-plan compiler when the plan is not applicable. Set `applies_outside_plan=true` only when the same
rule is intentionally both global and plan-associated.

This avoids duplicate numeric semantics while making meal-context application explicit.

A plan binding retains the exact referenced target/goal snapshot semantics even if that object is later
superseded by an unrelated Person energy-profile recalculation. Outside a plan, the compiler continues to use
only the current active target/goal. This prevents a professional plan from changing as a side effect of a
later weight/activity update.

## Qualitative and frequency guidance

Instructions that cannot be represented correctly by `NutritionConstraint` or `NutritionTargetComponent` use
`NutritionPlanGuideline`.

Two initial guideline types exist:

### qualitative

Examples:

```text
prefer vegetables at lunch
prefer unsaturated fats
choose lean protein where practical
```

Qualitative guidance has no occurrence count or period.

### frequency

Examples:

```text
fish >= 3 meals/week
red meat <= 2 meals/week
```

The initial period is `week`. A frequency guideline must define a minimum and/or maximum occurrence count.

Guidelines preserve severity, mandatory/advisory intent, meal scope, validity, priority and confirmation state.
`proposed` or `rejected` parsed guidance is never included in the effective active plan; only `confirmed`
guidance is compiled.

## EffectiveNutritionPlan compiler

The server-authoritative compiler resolves the guidance applicable to:

```text
Person + date + meal type
```

It combines:

1. applicable active/versioned Nutrition Plans;
2. their scoped rule bindings;
3. confirmed plan guidelines;
4. standalone Person NutritionConstraints;
5. the current active NutritionTarget components;
6. current active NutritionGoals.

Rules are not silently collapsed. They are returned with provenance and deterministic priority.

Initial source precedence is:

```text
clinician / nutritionist
> user
> imported
> system
```

Mandatory rules receive an additional priority tier above advisory rules. Local binding/guideline priority is
then applied inside that source tier.

Priority controls deterministic ordering only. It does not erase lower-priority guidance.

## Conflict handling

Numeric rules with the same target type, target key and unit are checked for incompatible minimum/maximum
ranges. If the effective minimum exceeds the effective maximum, the compiler returns an explicit conflict.
A conflict between two mandatory rules is marked mandatory; otherwise it is advisory.

The compiler does not invent a resolution. Later UI and Plan-Fit layers must show the conflict and preserve
both source statements.

## Evidence boundary

The effective plan describes requirements. It does not claim that a candidate meal has the evidence needed to
evaluate them. Numeric rules and guidelines therefore carry `requires_candidate_evidence=true`.

Meal nutrition evidence remains governed by the existing Food/Recipe composition and provenance model.
Missing candidate evidence must remain unknown and will be handled explicitly by Meal Plan-Fit; it must never
be interpreted as zero.

## API surface

Person-scoped endpoints support:

```text
GET/POST   /api/persons/{person_id}/nutrition-plans
GET/PATCH  /api/persons/{person_id}/nutrition-plans/{plan_id}
DELETE     /api/persons/{person_id}/nutrition-plans/{plan_id}          # draft only
POST       /api/persons/{person_id}/nutrition-plans/{plan_id}/versions
POST/DELETE plan rule bindings
POST/PUT/DELETE plan guidelines
GET        /api/persons/{person_id}/effective-nutrition-plan
```

The effective endpoint currently requires `on_date` and `meal_type`. Broader schedule, daily-state and weekly
progress context can extend this compiler without changing the underlying plan model.
