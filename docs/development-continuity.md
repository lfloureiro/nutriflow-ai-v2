# NutriFlow AI v2 development continuity

This is the authoritative handover entry point for NutriFlow AI v2. Repository code, migrations, tests, domain docs and ADRs take precedence over conversation history.

## Repository checkpoint

Nutrition Plan / Guidance has progressed through these capability blocks:

```text
PR #37  NutritionPlan + EffectiveNutritionPlan foundation
PR #38  reviewed text import / confirmation boundary
PR #39  deterministic Meal Plan-Fit evaluation + focused test UI
PR #42  AI-assisted text interpretation + browser review UI
PR #43  Structured Meal Transformation proposals                 IN PROGRESS
```

Last confirmed merged `main` before PR #43:

```text
83fbe4aa69f2adda7fb96be5df8c6be5d97598f3
```

PR #43 was created from that exact main on branch:

```text
feature/meal-transformation-proposals
```

Its feature schema head is:

```text
d2e6f1a9c4b7
```

Do not treat any SHA in this file as permanently current. At every new session resolve `refs/heads/main`, inspect open PRs and confirm CI on the exact final head before merging or starting new work.

The API test environment currently caps development/test AnyIO below 4.15 because Starlette 1.6.0 TestClient still imports a deprecated AnyIO alias and this repository treats warnings as errors.

## Product direction

NutriFlow AI v2 is a person-centric adaptive nutrition platform inside Family context. The product converts nutrition guidance into concrete meal decisions while keeping professional guidance, user preferences, evidence quality and practical availability distinct.

The operational chain is now:

```text
Person / Family
-> goals, targets, constraints
-> versioned NutritionPlan
-> EffectiveNutritionPlan per date + meal
-> source text -> proposed interpretations -> explicit review -> draft plan
-> FoodItem / Recipe composition evidence
-> MealPlanFit for one candidate + portion
-> Structured Meal Transformation proposals
-> Family meal planning / Servings
-> pantry / shopping
-> recommendation / feedback / diversity
-> normalized restaurant / delivery catalogue abstractions
```

Authoritative roadmap: `docs/vision/nutrition-plan-guidance-roadmap.md`.

Core plan/transformation docs:

- `docs/domain/nutrition-plan-model.md`
- `docs/domain/nutrition-plan-import-review.md`
- `docs/domain/meal-transformation.md`
- `docs/decisions/ADR-035-nutrition-plan-guidance-foundation.md`
- `docs/decisions/ADR-036-nutrition-plan-import-review-boundary.md`
- `docs/decisions/ADR-037-meal-plan-fit-evaluation.md`
- `docs/decisions/ADR-038-ai-assisted-nutrition-plan-import.md`
- `docs/decisions/ADR-039-structured-meal-transformation-proposals.md`

## Core invariants

Preserve these rules:

- Person is the primary nutrition entity inside Family context.
- One shared MealEvent can have multiple MealParticipants and Person-specific Servings.
- Normal meal types are exactly `breakfast`, `lunch`, `snack`, `dinner`.
- Nutrition Plan is distinct from Meal Plan.
- Active professional-plan content is immutable; substantive changes create a new version.
- Source/provenance and original statements remain traceable.
- Parser/AI interpretations never silently become active professional rules.
- Imported proposals must be explicitly confirmed/rejected before materialization; apply leaves the plan draft and activation stays separate.
- Missing nutrition evidence is unknown, never silently zero.
- Unsafe unit conversions are rejected rather than guessed.
- Mandatory adverse reactions and mandatory nutrition rules are hard gates before preferences/ranking/ML.
- Mandatory missing evidence/context fails closed where evaluation is safety-relevant.
- A numeric fit score never overrides a mandatory failure, conflict or safety block.
- Daily guidance must not be naively interpreted as a per-meal target.
- User preference remains separate from nutrition/practical fit.
- Professional guidance is not silently overridden by lower-authority guidance.
- Conflicts are surfaced, not silently resolved.
- Historical Servings and composition provenance remain stable when catalogue data changes.
- Structured transformations never silently mutate their source Recipe.
- Ingredient equivalence is explicit transformation metadata, not inferred from names or same-weight assumptions.
- Browser code presents server-authoritative nutrition/planning evidence.
- Demo/synthetic evidence remains explicitly development-only.
- Persisted timezones are valid IANA names.

## Nutrition Plan chain

### PR #37 — plan foundation

Implemented Person-scoped NutritionPlan lineage/versioning, source provenance, typed rules and guidelines, immutable active content, and deterministic EffectiveNutritionPlan compilation with explicit conflicts and precedence.

### PR #38 — import/review boundary

Implemented NutritionPlanImportSession/Proposal staging, conservative deterministic PT/EN parsing, proposed/confirmed/rejected review states, `unclassified` ambiguity handling, and materialization of confirmed content into a draft plan. Activation remains separate.

### PR #42 — AI-assisted import and review UI

Implemented an optional AI interpretation adapter using structured output while preserving the same import/review boundary. AI output always enters as proposed content and requires explicit user confirmation/rejection. The deterministic parser remains available without AI configuration.

The focused browser surface lives under the selected Person's Nutrition area. Text can be pasted and reviewed there.

AI configuration:

```text
OPENAI_API_KEY
NUTRIFLOW_NUTRITION_PLAN_AI_MODEL   default: gpt-5.6-luna
OPENAI_BASE_URL                     optional
```

Deferred import work is now primarily PDF/photo/document extraction. Extracted text must feed the existing review flow rather than creating a second trust boundary.

### PR #39 — Meal Plan-Fit

Implemented:

- `POST /api/persons/{person_id}/meal-plan-fit`;
- FoodItem/Recipe composition scaling with safe conversion;
- EffectiveNutritionPlan as rule source;
- direct evaluation of meal-scoped numeric rules;
- global nutrient rules treated as daily context;
- DailyNutritionState projected totals;
- `support` semantics for daily minimum/range progress;
- fail-closed mandatory missing context/evidence;
- adverse reactions and mandatory conflicts as hard gates;
- secondary 0..1 fit score that never overrides eligibility;
- qualitative/frequency guidance shown but not guessed/scored;
- focused Person Nutrition UI.

Development breakfast plan:

```text
breakfast protein >= 15 g   mandatory
breakfast fiber   >= 6 g    advisory
prefer whole fruit          qualitative / visible / not scored
```

Useful development cases:

```text
Iogurte grego, muesli e frutos vermelhos  -> 100%, eligible
Iogurte, muesli e banana                  -> ~96.67%, blocked by protein
Cereais com leite                         -> ~66.67%, blocked
```

## Phase 5 — Structured Meal Transformation

PR #43 implements the first complete proposal slice.

### Persistence

`FoodTransformationProfile` is Family-scoped and stores:

- FoodItem;
- explicit `substitution_group`;
- optional typical quantity/unit;
- enable flag;
- source/source-reference provenance.

This is transformation knowledge, not transformed Recipe persistence.

### Proposal engine

Endpoint:

```text
POST /api/persons/{person_id}/meal-transformations/proposals
```

v1 flow:

```text
Recipe + portion
-> baseline MealPlanFit
-> find explicit same-group ingredient alternatives
-> derive replacement quantity from explicit typical portions
-> calculate virtual replacement nutrition
-> after MealPlanFit
-> return only demonstrably improving proposals
```

A proposal can qualify because it resolves an eligibility block, improves meal Plan-Fit, or improves daily-rule progress. Mandatory safety/plan gates remain authoritative.

v1 performs one `replace_ingredient` operation at a time. It does not mutate the source Recipe and does not persist the virtual variant.

### Development example

Explicit synthetic development evidence defines:

```text
cultured-dairy-yogurt
  natural yogurt  typical portion 170 g
  Greek yogurt    typical portion 170 g
```

For `Iogurte, muesli e banana`:

```text
baseline ~= 96.67%, blocked by mandatory protein >= 15 g
Iogurte natural 170 g -> Iogurte grego 170 g
result = 100%, eligible
```

The existing Plan-Fit panel adds progressive disclosure after evaluation:

```text
Avaliar
-> Sugerir melhoria
-> replacement card with before/after fit and mandatory-block resolution
```

Tests cover the deterministic service, HTTP endpoint and development seed idempotence.

Deferred transformation work:

- explicit accept/materialize action to create a persistent Recipe variant;
- multi-operation transformation;
- ADD / REMOVE / REDUCE / INCREASE / CHANGE_COOKING_METHOD / CHANGE_PORTION;
- pantry/cost/preparation-time optimization;
- AI/learned candidate generation without explicit structured evidence.

## Existing supporting foundation

Already implemented elsewhere:

- Family/Person profiles, anthropometric history, energy profiles, goals, targets and constraints;
- health connection/measurement foundations and DailyHealthState/DailyNutritionState;
- versioned FoodItem and Recipe composition evidence;
- deterministic recipe nutrition;
- Family meal planning and Person-specific Servings;
- pantry and durable shopping lists;
- hard-rule-first recommendation engine, preferences, practical context, diversity/history and feedback;
- persisted recommendation runs/decisions;
- normalized availability/commercial-offer abstractions for home, pantry, restaurant, delivery and store;
- external menu ingestion into ordinary FoodItem/composition evidence.

Provider access remains outside core nutrition logic. Do not create provider-specific Plan-Fit engines.

## Frontend information architecture

Keep progressive disclosure and focused screens:

```text
Início
Refeições
Pessoas
Casa
Mais
```

Important areas:

```text
Refeições -> Hoje | Semana | Recomendar
Casa      -> Receitas | Ingredientes | Despensa | Compras | Preferências
Pessoas   -> Visão geral | Nutrição | Atividade | Saúde | Histórico | Perfil
```

Nutrition Plan, plan import, Plan-Fit and transformation proposals live under the selected Person's Nutrition context; meal planning remains under Refeições.

## Roadmap state

```text
0. Reconfirm baseline                                                     DONE
1. NutritionPlan domain/provenance                                        DONE
2. EffectiveNutritionPlan compiler                                        FOUNDATION DONE
3. Plan import/parser + explicit confirmation                             DONE
3b. AI-assisted text interpretation + browser review                      DONE (v1)
4. Meal Plan-Fit evaluation/explanations                                  DONE (v1)
5. Structured Meal Transformation proposals                               DONE (v1 slice, PR #43)
6. Home/pantry/recipe recommendations consuming Plan-Fit                   NEXT
7. Restaurant/delivery recommendations consuming the same Plan-Fit         PENDING
8. Weekly adaptive planning + frequency progress                           PENDING
9. Feedback/learning refinement                                            PENDING
```

The immediate architectural priority after PR #43 is to stop legacy recommendation nutrition scoring from diverging from MealPlanFit. Nutrition eligibility/fit should come from MealPlanFit; practical availability, preference and diversity remain separate ranking layers.

## Known broader limitations

- production authentication / Family authorization are not implemented;
- Family UUID remains development context;
- purchased ShoppingListItem does not automatically create PantryStockLot;
- catalogue evidence quality is incomplete and remains visible;
- consumer marketplace discovery depends on provider access/configuration;
- PDF/photo/document extraction into plan import is deferred;
- weekly frequency progress is deferred;
- qualitative/frequency automatic Plan-Fit evaluation is deferred;
- recommendation ranking has not yet been refactored to consume MealPlanFit directly;
- transformation proposals are not yet persistent Recipe variants;
- production npm lockfile / `npm ci` hardening remains pending.

## Delivery workflow

For each functional block:

1. resolve exact `main` SHA;
2. create focused branch from it;
3. build code/tests/docs together;
4. migrations only when persistence changes;
5. warnings are failures;
6. validate GitHub Actions on the exact final PR head;
7. never rely on checks from an earlier head;
8. verify mergeability and unchanged head;
9. guarded squash merge using expected head SHA;
10. verify resulting `main` before new work.

Never use `docker compose down -v` as a routine reset because the local PostgreSQL volume may contain user-created data.

## Resume procedure

At a new session:

1. resolve current `main`, open PRs and schema head;
2. read this file plus ADR-035 through ADR-039 as relevant;
3. if PR #43 remains open, validate exact-head API/Web CI, fix failures, verify mergeability and merge with expected head;
4. reproduce the browser transformation demo after merge;
5. next refactor home/pantry/Recipe recommendation nutrition evaluation onto MealPlanFit;
6. keep provider-specific discovery outside the common nutrition evaluator.
