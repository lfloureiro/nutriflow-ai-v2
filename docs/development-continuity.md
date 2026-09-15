# NutriFlow AI v2 development continuity

This is the authoritative handover entry point for NutriFlow AI v2. Repository code, migrations, tests, domain docs and ADRs take precedence over conversation history.

## Repository checkpoint

Nutrition Plan / Guidance has progressed through four capability blocks:

```text
PR #37  NutritionPlan + EffectiveNutritionPlan foundation
PR #38  reviewed text import / confirmation boundary
PR #39  deterministic Meal Plan-Fit evaluation + focused test UI
schema   c1f4a8d2e6b9
```

PR #38 merged into `main` as:

```text
c65b885ef006abe5b467a3072b48eacd91b05fc4
```

PR #39 was created from that exact main. Its functional head `6df5de2687d5eb47e61c02915854a9ccd41f4cea` passed PostgreSQL migrations, `alembic check`, Ruff, 234 API tests and Web CI. Documentation commits move the final PR head, so validate the exact final head again before merge.

Do not treat any SHA in this file as permanently current. At every new session resolve `refs/heads/main`, inspect open PRs and confirm CI before creating new work.

The API test environment currently caps development/test AnyIO below 4.15 because Starlette 1.6.0 TestClient still imports a deprecated AnyIO alias and this repository treats warnings as errors.

## Product direction

NutriFlow AI v2 is a person-centric adaptive nutrition platform inside Family context. The product should convert nutrition guidance into concrete meal decisions while keeping professional guidance, user preferences, evidence quality and practical availability distinct.

The operational chain now includes:

```text
Person / Family
-> goals, targets, constraints
-> versioned NutritionPlan
-> EffectiveNutritionPlan per date + meal
-> source text -> proposed interpretations -> explicit review -> draft plan
-> FoodItem / Recipe composition evidence
-> MealPlanFit for one candidate + portion
-> Family meal planning / Servings
-> pantry / shopping
-> recommendation / feedback / diversity
-> normalized restaurant / delivery catalogue abstractions
```

Authoritative roadmap: `docs/vision/nutrition-plan-guidance-roadmap.md`.

Core plan docs:

- `docs/domain/nutrition-plan-model.md`
- `docs/domain/nutrition-plan-import-review.md`
- `docs/decisions/ADR-035-nutrition-plan-guidance-foundation.md`
- `docs/decisions/ADR-036-nutrition-plan-import-review-boundary.md`
- `docs/decisions/ADR-037-meal-plan-fit-evaluation.md`

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
- Browser code presents server-authoritative nutrition/planning evidence.
- Demo/synthetic evidence remains explicitly development-only.
- Persisted timezones are valid IANA names.

## Implemented Nutrition Plan chain

### PR #37 — plan foundation

Implemented:

- Person-scoped `NutritionPlan` lineage/version/supersession lifecycle;
- `draft`, `active`, `inactive`, `superseded` states;
- source type/name/reference and original source text;
- immutable active plan content and draft-only mutation;
- typed `NutritionPlanRule` links to NutritionConstraint, NutritionTargetComponent and NutritionGoal;
- meal scope, priority, validity and source statement per binding;
- qualitative and weekly-frequency `NutritionPlanGuideline`;
- deterministic `EffectiveNutritionPlan` compiler for Person + date + meal type;
- mandatory/source precedence ordering without silently deleting lower-priority guidance;
- numeric conflict reporting;
- Person-scoped plan/version/rule/guideline API.

### PR #38 — import/review boundary

Implemented:

- `NutritionPlanImportSession` and `NutritionPlanImportProposal` staging;
- deterministic conservative PT/EN text parser v1;
- numeric nutrient values/ranges, meal scope, weekly food-category frequencies and qualitative directives;
- `unclassified` fallback instead of guessing;
- proposal confidence, parser notes, verbatim source statement and review notes;
- explicit proposed/confirmed/rejected review states;
- atomic proposal edits;
- all proposals reviewed before apply;
- confirmed numeric proposals -> NutritionConstraint + NutritionPlanRule;
- confirmed qualitative/frequency proposals -> confirmed NutritionPlanGuideline;
- materialized plan remains draft until separately activated;
- imported plan-only constraints are not duplicated by EffectiveNutritionPlan.

Deferred import work: PDF/photo/document extraction, LLM parser adapter and focused plan-import review UI.

### PR #39 — Meal Plan-Fit

Implemented backend slice:

- `POST /api/persons/{person_id}/meal-plan-fit`;
- reuse of existing FoodItem/Recipe candidate normalization and versioned composition scaling;
- safe unit conversion using the existing serving-nutrition boundary;
- evaluation against server-compiled `EffectiveNutritionPlan`;
- meal-scoped nutrient rules evaluated directly against candidate evidence;
- candidate-level exclusion subjects evaluated directly;
- global nutrient rules treated as daily-context rules rather than per-meal targets;
- latest matching DailyNutritionState auto-selected when an explicit state id is not supplied;
- daily projected totals use current consumed/planned state plus candidate evidence;
- daily minimum/range guidance can return `support` when the candidate moves the day toward the target without needing one meal to complete the full target;
- mandatory daily rules with missing state/evidence return `unknown` and fail closed;
- mandatory adverse reactions remain independent hard gates;
- mandatory EffectiveNutritionPlan conflicts block eligibility;
- rule statuses `pass`, `fail`, `support`, `unknown`, `not_evaluated`;
- overall statuses `pass`, `partial`, `fail`, `unknown`, `conflict`;
- `fit_score` is a secondary 0..1 mean for scored candidate/meal numeric rules only and never overrides eligibility;
- qualitative/frequency guidance remains visible with provenance but explicitly unscored in v1;
- Recipe and FoodItem share the same evaluator contract;
- no database migration required.

Implemented focused web test slice:

```text
Pessoas -> <Person> -> Nutrição -> Adequação ao plano
```

The panel lets the user choose meal type, an existing Recipe and portion, then shows fit %, eligibility/blocking state, active plan, rule-by-rule target/observed/projected values, conflicts, safety issues and unscored guidance. It deliberately reuses the existing Person Nutrition screen instead of adding a dense dashboard.

Development data now includes an explicit demo breakfast plan for the technical demo Person:

```text
breakfast protein >= 15 g   mandatory
breakfast fiber   >= 6 g    advisory
prefer whole fruit          qualitative / visible / not scored
```

The existing demo daily sodium maximum remains useful for exercising daily-context Plan-Fit.

## Existing supporting foundation

Already implemented elsewhere in the repository:

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

Provider access remains outside the core nutrition logic. Do not create provider-specific Plan-Fit engines.

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

Nutrition Plan and Plan-Fit live under the selected Person's Nutrition context; meal planning remains under Refeições.

## Roadmap state

```text
0. Reconfirm baseline                                                     DONE
1. NutritionPlan domain/provenance                                        DONE
2. EffectiveNutritionPlan compiler                                        FOUNDATION DONE
3. Plan import/parser + explicit confirmation                             DONE
4. Meal Plan-Fit evaluation/explanations                                  DONE (v1 slice)
5. Structured Meal Transformation proposals                               NEXT
6. Home/pantry/recipe recommendations consuming Plan-Fit                   PENDING
7. Restaurant/delivery recommendations consuming the same Plan-Fit         PENDING
8. Weekly adaptive planning + frequency progress                           PENDING
9. Feedback/learning refinement                                            PENDING
```

Before Phase 5, consider a small integration step that replaces duplicated nutrition-rule evaluation inside recommendation ranking with the new MealPlanFit contract. Do not let old and new nutrition scoring diverge.

## Immediate next work

After PR #39 is merged and user-tested, the next logical branch is:

```text
feature/meal-transformation-proposals
```

Target Phase 5 flow:

```text
existing meal candidate
-> baseline MealPlanFit
-> structured transformation operations
   ADD / REMOVE / REDUCE / INCREASE / SWAP / CHANGE_COOKING_METHOD / CHANGE_PORTION
-> recalculated candidate evidence
-> after MealPlanFit
-> explain score/eligibility delta and rationale
```

Do not start provider-specific Uber Eats/Glovo scoring. Restaurant/delivery items should continue to enter through normalized FoodItem/composition evidence and the same evaluator.

## Known broader limitations

- production authentication / Family authorization are not implemented;
- Family UUID remains development context;
- purchased ShoppingListItem does not automatically create PantryStockLot;
- catalogue evidence quality is incomplete and remains visible;
- consumer marketplace discovery depends on provider access/configuration;
- PDF/photo/document and LLM plan ingestion adapters are deferred;
- focused plan-import review UI is deferred;
- qualitative and weekly-frequency Plan-Fit evaluation/progress is deferred;
- recommendation ranking has not yet been refactored to consume MealPlanFit directly;
- Meal Transformation is not implemented;
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

1. read this file and the nutrition-plan roadmap;
2. inspect current `main`, open PRs and schema head;
3. read ADR-035, ADR-036 and ADR-037;
4. confirm API/Web validation baseline;
5. if PR #39 is not merged, finish exact-head CI and merge first;
6. if it is merged, reproduce the browser Plan-Fit demo before Phase 5;
7. keep recommendation integration and transformation based on the common MealPlanFit boundary rather than a second nutrition scorer.
