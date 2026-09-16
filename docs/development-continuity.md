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
PR #45  scoped single-Person recommendations consume Meal Plan-Fit         MERGED
PR #46  shared-family recommendations use Person-specific Meal Plan-Fit    MERGED
PR #47  restaurant/delivery recommendations consume Meal Plan-Fit          MERGED
Phase 8 weekly frequency progress foundation                              IN PROGRESS
```

Confirmed `main` after PR #47:

```text
bb5a700c8ef80c0b74fa455d4fe6c5bc6a33775e
```

Current Phase 8 branch:

```text
feature/weekly-frequency-progress
```

The current Phase 8 slice adds no migration. Repository schema head remains:

```text
d2e6f1a9c4b7
```

Do not treat any SHA in this file as permanently current. At every new session resolve `refs/heads/main`, inspect open PRs and confirm CI on the exact final head before merging or starting new work.

The API test environment currently caps development/test AnyIO below 4.15 because Starlette 1.6.0 TestClient still imports a deprecated AnyIO alias and this repository treats warnings as errors.

## Product direction

NutriFlow AI v2 is a Person-centric adaptive nutrition platform inside Family context. Professional guidance is compiled once into authoritative planning evidence and then reused by meal evaluation, recommendations and week-level planning.

Current operational chain:

```text
Person / Family
-> goals, targets, constraints
-> versioned NutritionPlan
-> EffectiveNutritionPlan per date + meal
-> reviewed text/document import
-> FoodItem / Recipe composition + planning metadata
-> MealPlanFit for one candidate + exact portion
-> Structured Meal Transformation proposals
-> single-Person / shared-Family / external recommendation paths
-> practical availability + preference + diversity + feedback
-> Family MealEvent + Person-specific Servings
-> weekly frequency progress from structured meal evidence
-> future adaptive weekly planning
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
- ADR-042 shared-family recommendations use Person-specific Meal Plan-Fit
- ADR-043 external commercial recommendations use normalized persisted evidence and Meal Plan-Fit
- ADR-044 weekly frequency progress uses structured meal evidence

## Core invariants

Preserve these rules:

- Person is the primary nutrition entity inside Family context.
- One shared MealEvent can have multiple MealParticipants and Person-specific Servings.
- Normal meal types are exactly `breakfast`, `lunch`, `snack`, `dinner`.
- Nutrition Plan is distinct from Meal Plan.
- Active professional-plan content is immutable; substantive changes create a new version.
- Source/provenance and original statements remain traceable.
- Parser/AI interpretations never silently become active professional rules.
- Missing nutrition or classification evidence is unknown, never silently zero.
- Unsafe unit conversions are rejected rather than guessed.
- Mandatory adverse reactions and mandatory nutrition rules are hard gates before preferences/ranking/ML.
- A numeric fit score never overrides a mandatory failure, conflict or safety block.
- Daily guidance must not be naively interpreted as a per-meal target.
- User preference remains separate from nutrition/practical fit.
- Professional guidance is not silently overridden by lower-authority guidance.
- Conflicts are surfaced, not silently resolved.
- Historical Servings and composition provenance remain stable when catalogue data changes.
- Structured transformations never silently mutate their source Recipe.
- Practical availability, price, family preference, diversity and feedback may rank an eligible meal but may not reverse Meal Plan-Fit ineligibility.
- Shared-family Plan-Fit is Person-specific; one Person's plan must never be copied to another Person.
- External items without persisted composition evidence are not nutrition-ranked.
- Weekly frequency evaluation never classifies food from names/descriptions; only persisted structured planning evidence may count.
- Browser code presents server-authoritative nutrition/planning evidence.
- Persisted timezones are valid IANA names.

## Recommendation integration

Single-Person, shared-Family and external restaurant/delivery production recommendation paths now consume the common Meal Plan-Fit semantics when an explicit meal scope exists.

External restaurant/delivery observations are normalized to ordinary catalogue abstractions:

```text
FoodItem
+ optional versioned FoodCompositionSnapshot
+ MealCandidateAvailability
+ MealCommercialOffer
```

Commercial items without nutrition composition remain visible but unranked. Price/provider/preference cannot override mandatory Plan-Fit failure.

## Phase 8 — weekly frequency progress

The current branch adds a deterministic, server-authoritative read model and endpoint:

```text
GET /api/persons/{person_id}/weekly-frequency-progress?on_date=YYYY-MM-DD
```

The endpoint:

- resolves Monday-Sunday in the Person's persisted IANA timezone;
- obtains confirmed weekly `frequency` guidance from the existing EffectiveNutritionPlan compiler;
- counts Person-specific MealParticipant/Serving evidence only;
- excludes cancelled/replaced events and skipped/replaced participants/servings;
- separates completed from planned occurrences;
- counts one MealEvent at most once per guideline;
- reports minimum/maximum progress, remaining minimum/capacity and occurrence provenance;
- marks counts as a lower bound when relevant meals lack enough structured classification evidence;
- keeps unsupported targets `unknown`, with numeric occurrence/progress fields `null` rather than zero.

Structured target support in v1:

```text
food_category       canonical Nutrition Plan import vocabulary
food_group          backward-compatible alias
planning_category
primary_protein
food_item
recipe
```

`food_category`/`food_group` are resolved only from explicit `MealCandidatePlanningProfile.planning_category` or `primary_protein`. Food names and descriptions are never used as classification evidence.

Focused regression coverage includes:

- Person-specific counting inside shared Family events;
- completed vs planned evidence;
- weekly minimum achieved and maximum exceeded states;
- cancelled/replaced exclusion;
- Lisbon local-week boundary handling;
- unclassified meals producing lower-bound counts;
- unsupported target evidence staying `unknown`/`null`;
- canonical imported `food_category=fish` matching explicit `primary_protein=fish`.

This is only the Phase 8 evidence foundation. It does not yet mutate recommendations or optimize a full week.

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

Nutrition Plan, import, Plan-Fit and weekly guidance evidence belong to the selected Person's Nutrition context; operational meal planning remains under Refeições.

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
6. Home/pantry/recipe recommendations consuming Plan-Fit                  DONE (v1)
6b. Shared-family Person-specific Plan-Fit                                DONE (v1)
7. Restaurant/delivery recommendations consuming same Plan-Fit            DONE (v1)
8. Weekly adaptive planning + frequency progress                          IN PROGRESS
8a. Deterministic weekly frequency progress                               IN PROGRESS (current branch)
8b. Week-level adaptive candidate selection/optimization                  PENDING
9. Feedback/learning refinement                                           PENDING
```

OCR/photo import remains a parallel capability gap, not a reason to create a second plan-import trust boundary.

## Known limitations / technical debt

- production authentication / Family authorization are not implemented;
- Family UUID remains development context;
- catalogue classification/evidence quality remains incomplete and visible;
- consumer marketplace discovery depends on provider access/configuration;
- external items without composition remain intentionally unranked;
- OCR/photo/scanned-PDF extraction is deferred;
- weekly progress v1 does not yet optimize future meals or hard-gate a future candidate against a weekly maximum;
- richer reviewed food-category taxonomy/equivalence is deferred;
- qualitative guidance remains visible but is not automatically guessed/scored;
- unscoped recommendation still has the legacy nutrition evaluator;
- MealPlanFit still imports private candidate-loading helpers from recommendation API; extract a public common service later;
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
2. read this file and ADR-044;
3. if the weekly-frequency branch/PR is active, inspect API/Web CI on the exact latest head;
4. verify `food_category` import vocabulary, Person-specific counting, lower-bound semantics and unsupported-target `null` behavior;
5. guarded squash-merge only after exact-head CI is green and the PR head is unchanged/mergeable;
6. verify post-merge `main` CI;
7. continue Phase 8 by making adaptive weekly planning consume this frequency-progress evidence rather than creating another frequency evaluator.
