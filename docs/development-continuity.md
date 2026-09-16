# NutriFlow AI v2 development continuity

This is the authoritative handover entry point for NutriFlow AI v2. Repository code, migrations, tests, domain docs and ADRs take precedence over conversation history.

## Repository checkpoint

Nutrition Plan / Guidance capability blocks:

```text
PR #37  NutritionPlan + EffectiveNutritionPlan foundation                 MERGED
PR #38  reviewed text import / confirmation boundary                      MERGED
PR #39  deterministic Meal Plan-Fit evaluation + focused test UI          MERGED
PR #42  AI-assisted text interpretation + browser review UI               MERGED
PR #43  Structured Meal Transformation proposals                          MERGED
PR #44  PDF/DOCX/TXT/Markdown text extraction into import review          MERGED
PR #45  scoped recommendations consume Meal Plan-Fit                       IN PROGRESS
```

Confirmed `main` after PR #44:

```text
696deea17ddb46db076f97e041a0831439de1e05
```

PR #45 was created from that exact main on:

```text
feature/recommendations-consume-meal-plan-fit
```

PR #45 adds no migration. Current schema head remains:

```text
d2e6f1a9c4b7
```

Do not treat any SHA in this file as permanently current. At every new session resolve `refs/heads/main`, inspect open PRs and confirm CI on the exact final head before merging or starting new work.

The API test environment currently caps development/test AnyIO below 4.15 because Starlette 1.6.0 TestClient still imports a deprecated AnyIO alias and this repository treats warnings as errors.

## Product direction

NutriFlow AI v2 is a Person-centric adaptive nutrition platform inside Family context. The product converts nutrition guidance into concrete meal decisions while keeping professional guidance, user preference, evidence quality and practical availability distinct.

Current operational chain:

```text
Person / Family
-> goals, targets, constraints
-> versioned NutritionPlan
-> EffectiveNutritionPlan per date + meal
-> source text/document -> editable extracted text -> proposed interpretations
-> explicit review -> draft plan -> separate activation
-> FoodItem / Recipe composition evidence
-> MealPlanFit for one candidate + exact portion
-> Structured Meal Transformation proposals
-> meal recommendation eligibility/fit
-> practical availability + preference + diversity + feedback
-> Family meal planning / Person-specific Servings
-> pantry / shopping
-> normalized restaurant / delivery catalogue abstractions
```

Authoritative roadmap: `docs/vision/nutrition-plan-guidance-roadmap.md`.

Key ADRs:

- ADR-035 Nutrition Plan guidance foundation
- ADR-036 Nutrition Plan import/review boundary
- ADR-037 Meal Plan-Fit evaluation
- ADR-038 AI-assisted Nutrition Plan import
- ADR-039 Structured Meal Transformation proposals
- ADR-040 document extraction feeds the review boundary
- ADR-041 scoped recommendations consume Meal Plan-Fit

## Core invariants

Preserve these rules:

- Person is the primary nutrition entity inside Family context.
- One shared MealEvent can have multiple MealParticipants and Person-specific Servings.
- Normal meal types are exactly `breakfast`, `lunch`, `snack`, `dinner`.
- Nutrition Plan is distinct from Meal Plan.
- Active professional-plan content is immutable; substantive changes create a new version.
- Source/provenance and original statements remain traceable.
- Parser/AI interpretations never silently become active professional rules.
- Document extraction is only an input adapter; extracted text must still cross the same review boundary.
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
- Practical availability, family preference, diversity and feedback may rank an eligible meal but may not reverse Meal Plan-Fit ineligibility.
- If Plan-Fit is eligible but numerically unscored, missing score is omitted rather than converted to zero.
- Provider-specific discovery remains outside the common nutrition evaluator.
- Browser code presents server-authoritative nutrition/planning evidence.
- Demo/synthetic evidence remains explicitly development-only.
- Persisted timezones are valid IANA names.

## Nutrition Plan chain

### PR #37 — plan foundation

Implemented Person-scoped NutritionPlan lineage/versioning, source provenance, typed rules and guidelines, immutable active content, and deterministic EffectiveNutritionPlan compilation with explicit conflicts and precedence.

### PR #38 / #42 / #44 — plan ingestion

The ingestion path is now:

```text
paste text
or PDF / DOCX / TXT / Markdown upload
-> bounded extraction when needed
-> editable source text
-> deterministic or AI interpretation
-> proposed structured statements
-> explicit confirm/reject review
-> apply confirmed proposals to a draft plan
-> separate activation
```

Document limits:

```text
10 MB upload
60 PDF pages
100,000 extracted characters
```

Unsupported, malformed, encrypted, empty and image-only/scanned PDFs fail explicitly. OCR/photo support is deferred and must feed the same editable-text/review boundary.

AI configuration:

```text
OPENAI_API_KEY
NUTRIFLOW_NUTRITION_PLAN_AI_MODEL   default: gpt-5.6-luna
OPENAI_BASE_URL                     optional
```

### PR #39 — Meal Plan-Fit

Implemented `POST /api/persons/{person_id}/meal-plan-fit` using EffectiveNutritionPlan and exact candidate composition/portion evidence.

Important semantics:

- meal-scoped numeric rules evaluated directly;
- daily rules evaluated against DailyNutritionState projected totals;
- mandatory conflicts/safety/evidence failures are hard gates;
- qualitative/frequency guidance is visible but not guessed/scored;
- fit score is secondary and cannot override eligibility.

Development breakfast cases:

```text
Iogurte grego, muesli e frutos vermelhos  -> 100%, eligible
Iogurte, muesli e banana                  -> ~96.67%, blocked by protein
Cereais com leite                         -> ~66.67%, blocked
```

### PR #43 — Structured Meal Transformation

Implemented Family-scoped `FoodTransformationProfile` and deterministic single-operation `replace_ingredient` proposals.

Flow:

```text
Recipe + portion
-> baseline MealPlanFit
-> explicit same-group ingredient alternatives
-> explicit portion-equivalence metadata
-> virtual replacement nutrition
-> after MealPlanFit
-> only demonstrably improving proposals
```

The source Recipe is never silently mutated.

Development example:

```text
Iogurte, muesli e banana
baseline ~= 96.67%, blocked by mandatory protein >= 15 g
Iogurte natural 170 g -> Iogurte grego 170 g
result = 100%, eligible
```

Deferred: persistent variant materialization, multi-operation transformation, cooking-method transformations and AI-inferred substitutions without explicit evidence.

## PR #45 — recommendation integration

Goal: remove the semantic split where recommendation ranking independently reinterpreted nutrition rules already handled by Meal Plan-Fit.

For single-Person recommendations with an explicit meal type:

```text
candidate + exact/final portion
-> Meal Plan-Fit
-> mandatory eligibility gate
-> Plan-Fit score when available
-> preference/advisory reaction
-> practical availability/context
-> family preference
-> diversity
-> feedback
```

Current PR #45 implementation covers:

- basic meal-scoped recommendation endpoint;
- practical home/pantry/commercial recommendation endpoint;
- optional portion sizing before Plan-Fit;
- Plan-Fit exclusion evidence persisted in recommendation decisions;
- explicit `nutrition_evaluator=meal-plan-fit-v1` run context;
- focused regression proving a preferred candidate cannot outrank a mandatory professional-plan failure.

Intentional temporary fallbacks:

- recommendation calls without `meal_type` keep the legacy evaluator because current MealPlanFit requires an explicit meal type;
- shared-Family recommendation remains legacy until participant-specific Plan-Fit evidence is represented correctly.

Do not approximate either case by applying one Person's plan to everyone or by inventing a meal scope.

## Existing supporting foundation

Already implemented elsewhere:

- Family/Person profiles, anthropometric history, energy profiles, goals, targets and constraints;
- health connection/measurement foundations and DailyHealthState/DailyNutritionState;
- versioned FoodItem and Recipe composition evidence;
- deterministic recipe nutrition;
- Family meal planning and Person-specific Servings;
- pantry and durable shopping lists;
- persisted recommendation runs/decisions, preferences, practical context, diversity/history and feedback;
- normalized availability/commercial-offer abstractions for home, pantry, restaurant, delivery and store;
- external menu ingestion into ordinary FoodItem/composition evidence.

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

Nutrition Plan, plan import, document upload, Plan-Fit and transformation proposals live under the selected Person's Nutrition context; meal planning remains under Refeições.

## Roadmap state

```text
0. Reconfirm baseline                                                     DONE
1. NutritionPlan domain/provenance                                        DONE
2. EffectiveNutritionPlan compiler                                        FOUNDATION DONE
3. Plan import/parser + explicit confirmation                             DONE
3b. AI-assisted text interpretation + browser review                      DONE (v1)
3c. PDF/DOCX/TXT/Markdown text extraction                                 DONE (v1)
4. Meal Plan-Fit evaluation/explanations                                  DONE (v1)
5. Structured Meal Transformation proposals                               DONE (v1)
6. Home/pantry/recipe recommendations consuming Plan-Fit                   IN PROGRESS (PR #45)
7. Restaurant/delivery recommendations consuming same Plan-Fit             PENDING
8. Weekly adaptive planning + frequency progress                           PENDING
9. Feedback/learning refinement                                            PENDING
```

After PR #45, the next integration step is shared-family participant-specific Plan-Fit and/or the restaurant/delivery path, while keeping the same common evaluator.

OCR/photo import remains a parallel capability gap, not a reason to create a second plan-import trust boundary.

## Known limitations / technical debt

- production authentication / Family authorization are not implemented;
- Family UUID remains development context;
- purchased ShoppingListItem does not automatically create PantryStockLot;
- catalogue evidence quality is incomplete and remains visible;
- consumer marketplace discovery depends on provider access/configuration;
- OCR/photo/scanned-PDF extraction is deferred;
- weekly frequency progress is deferred;
- qualitative/frequency automatic Plan-Fit evaluation is deferred;
- unscoped recommendation still has the legacy nutrition evaluator;
- shared-family recommendation still has the legacy participant evaluator;
- MealPlanFit still imports private candidate-loading helpers from recommendation API; move these to a public common service later;
- candidate-by-candidate Plan-Fit is correct but not yet batch-optimized;
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
2. read this file and the latest relevant ADRs;
3. if PR #45 is open, inspect exact-head API/Web CI and any regression-test failures;
4. fix existing recommendation expectations only where semantics intentionally changed to Plan-Fit;
5. verify mergeability and guarded squash-merge PR #45 only after exact-head CI is green;
6. verify post-merge `main` CI;
7. continue participant-specific/shared or external restaurant/delivery Plan-Fit integration without creating another nutrition evaluator.
