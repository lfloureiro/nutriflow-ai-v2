# Nutrition Plan import and review

## Purpose

This layer turns pasted nutrition-plan text into reviewable structured proposals without allowing parser output to become active guidance automatically.

The source plan and NutriFlow interpretation remain separate until the user explicitly confirms each proposal.

## Flow

```text
paste plan text
-> create draft NutritionPlan
-> create NutritionPlanImportSession
-> deterministic parser creates proposals
-> user edits / confirms / rejects every proposal
-> apply confirmed proposals
-> resulting NutritionPlan remains draft
-> user separately activates NutritionPlan
```

## NutritionPlanImportSession

One session belongs to one Person and one draft NutritionPlan.

Important fields:

```text
person_id
nutrition_plan_id
parser_name
parser_version
status: review | applied | cancelled
source_text
parse_summary
```

The source text is preserved exactly. The linked NutritionPlan also stores the original text as part of its normal provenance.

## NutritionPlanImportProposal

One proposal represents one source statement and its current interpretation.

Proposal types:

```text
numeric_rule
qualitative_guideline
frequency_guideline
unclassified
```

Review state:

```text
proposed
confirmed
rejected
```

A proposal preserves:

- source statement;
- normalized target type/key;
- operator and numeric values where applicable;
- meal scope;
- weekly-frequency fields;
- mandatory/advisory semantics;
- validity scope;
- parser confidence/note;
- human review notes;
- materialized rule/guideline ID after apply.

## Deterministic parser v1

Parser identity:

```text
name:    deterministic-text
version: nutrition-plan-text-v1
```

The parser is deliberately narrow rather than speculative.

It currently recognizes common Portuguese/English forms for:

- protein, fibre/fiber, sodium, energy/calories and saturated fat;
- exact values, minimums, maximums and ranges;
- breakfast, lunch, snack and dinner references;
- weekly frequencies for fish, pulses, red meat, vegetables, salad, fruit and nuts;
- qualitative directives such as prefer/reduce/avoid/choose.

Unknown statements are returned as `unclassified` with low confidence. Missing interpretation is visible; it is never converted to zero or invented data.

## Review rules

While the import is in `review`:

- proposals may be edited;
- proposals may be manually added;
- each proposal must end as confirmed or rejected before apply;
- the linked NutritionPlan must remain draft.

Once the import is `applied` or `cancelled`, proposal editing is closed.

A confirmed unclassified proposal blocks apply because confirmation alone does not make an unknown interpretation safe.

## Materialization

### Numeric proposals

Confirmed numeric proposals create:

```text
NutritionConstraint
+ NutritionPlanRule(rule_kind=constraint)
```

Advisory numeric targets use `constraint_type=nutrient_target`; mandatory numeric rules use `constraint_type=nutrient_limit`.

The created constraint preserves the plan source type/name/reference and the proposal source statement remains on the NutritionPlanRule.

### Qualitative/frequency proposals

Confirmed guideline proposals create a normal `NutritionPlanGuideline` with `confirmation_status=confirmed`.

### Important lifecycle boundary

Apply does **not** activate the plan.

The resulting plan remains draft so that the user can inspect the complete structured plan before using the existing NutritionPlan status transition to activate it.

## API

Person-scoped endpoints:

```text
GET  /api/persons/{person_id}/nutrition-plan-imports
POST /api/persons/{person_id}/nutrition-plan-imports
GET  /api/persons/{person_id}/nutrition-plan-imports/{import_id}
POST /api/persons/{person_id}/nutrition-plan-imports/{import_id}/proposals
PATCH /api/persons/{person_id}/nutrition-plan-imports/{import_id}/proposals/{proposal_id}
POST /api/persons/{person_id}/nutrition-plan-imports/{import_id}/apply
POST /api/persons/{person_id}/nutrition-plan-imports/{import_id}/cancel
```

## Future parser adapters

PDF/document/photo extraction and LLM-assisted interpretation should feed exactly this proposal contract.

They must not create NutritionConstraint, NutritionTarget, NutritionGoal or active NutritionPlan records directly. The review boundary remains mandatory regardless of parser technology.
