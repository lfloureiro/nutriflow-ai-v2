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
PR #48  deterministic weekly frequency progress                           MERGED
Phase 8b adaptive candidate selection from weekly frequency evidence       IN PROGRESS
```

Confirmed `main` after PR #48:

```text
e33659a394521d6f3b1ef3340c46b79f29316af7
```

Current Phase 8b branch:

```text
feature/weekly-adaptive-planning
```

The current slice adds no migration. Repository schema head remains:

```text
d2e6f1a9c4b7
```

Do not treat any SHA in this file as permanently current. At every new session resolve `refs/heads/main`, inspect open PRs and confirm CI on the exact final head before merging or starting new work.

The API test environment currently caps development/test AnyIO below 4.15 because Starlette 1.6.0 TestClient still imports a deprecated AnyIO alias and this repository treats warnings as errors.

## Product direction

NutriFlow AI v2 is a Person-centric adaptive nutrition platform inside Family context. Professional guidance is compiled once into authoritative planning evidence and reused by meal evaluation, recommendations and week-level planning.

Current operational chain:

```text
Person / Family
-> goals, targets, constraints
-> versioned NutritionPlan
-> EffectiveNutritionPlan per date + meal
-> reviewed text/document import
-> FoodItem / Recipe composition + explicit planning metadata
-> MealPlanFit for candidate + exact portion
-> Person-specific weekly frequency progress
-> weekly-aware MealPlanFit guideline evidence
-> Structured Meal Transformation proposals
-> single-Person / shared-Family / external recommendation paths
-> practical availability + preference + diversity + feedback
-> adaptive candidate ordering from weekly support
-> Family MealEvent + Person-specific Servings
-> future full-week optimization
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
- ADR-045 weekly frequency guidance extends Meal Plan-Fit

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
- Weekly minimum frequency guidance must not be naively interpreted as a per-meal mandatory target.
- Mandatory weekly maxima fail closed when remaining safe capacity cannot be established from the available structured evidence.
- User preference remains separate from nutrition/practical fit.
- Professional guidance is not silently overridden by lower-authority guidance.
- Conflicts are surfaced, not silently resolved.
- Historical Servings and composition provenance remain stable when catalogue data changes.
- Structured transformations never silently mutate their source Recipe.
- Practical availability, price, family preference, diversity and feedback may rank an eligible meal but may not reverse Meal Plan-Fit ineligibility.
- Shared-family Plan-Fit is Person-specific; one Person's plan must never be copied to another Person.
- External items without persisted composition evidence are not nutrition-ranked.
- Weekly frequency evaluation never classifies food from names/descriptions; only persisted structured planning evidence may count.
- Recommendation code consumes weekly evidence from Meal Plan-Fit rather than implementing another frequency evaluator.
- Browser code presents server-authoritative nutrition/planning evidence.
- Persisted timezones are valid IANA names.

## Recommendation integration

Single-Person, shared-Family and external restaurant/delivery production recommendation paths consume the common Meal Plan-Fit semantics when an explicit meal scope exists.

External restaurant/delivery observations are normalized to ordinary catalogue abstractions:

```text
FoodItem
+ optional versioned FoodCompositionSnapshot
+ MealCandidateAvailability
+ MealCommercialOffer
```

Commercial items without nutrition composition remain visible but unranked. Price/provider/preference cannot override mandatory Plan-Fit failure.

## Phase 8a — weekly frequency progress

PR #48 added the deterministic server-authoritative read model:

```text
GET /api/persons/{person_id}/weekly-frequency-progress?on_date=YYYY-MM-DD
```

It resolves Monday-Sunday in the Person's IANA timezone, consumes confirmed weekly frequency guidance from EffectiveNutritionPlan, counts Person-specific MealParticipant/Serving evidence, separates completed/planned occurrences, reports provenance and remaining minimum/capacity, and marks lower-bound counts when structured classification is incomplete.

Supported structured targets in v1:

```text
food_category
food_group
planning_category
primary_protein
food_item
recipe
```

`food_category`/`food_group` resolve only through explicit `MealCandidatePlanningProfile` metadata. Names and descriptions are never classification evidence. Unsupported targets remain `unknown` with numeric fields `null`.

## Phase 8b — weekly-aware adaptive candidate selection

The current branch extends production Meal Plan-Fit with the Phase 8a weekly evidence instead of introducing a separate nutrition evaluator.

For an explicit Person/date/meal/candidate:

```text
ordinary numeric/safety Meal Plan-Fit
-> weekly frequency progress
-> explicit candidate planning classification
-> weekly guideline status
-> final Meal Plan-Fit eligibility
-> recommendation ranking
```

Frequency guideline semantics:

- a candidate matching a confirmed remaining weekly minimum receives `support`;
- a non-matching candidate is not blocked by a weekly minimum because future meals can still satisfy it;
- a mandatory weekly maximum returns `fail` when the candidate would definitely exceed it;
- incomplete structured evidence returns `unknown` and fails closed when safe remaining capacity for a mandatory maximum cannot be proven;
- qualitative guidance remains visible but not automatically inferred/scored;
- weekly support is not folded into numeric `fit_score`.

Recommendation adaptation reads the weekly `support` evidence from Meal Plan-Fit. Among already eligible candidates it orders confirmed mandatory-minimum support first, then advisory-minimum support, then preserves the existing rank from Plan-Fit/preference/practical/diversity/feedback. Hard gates remain entirely owned by Meal Plan-Fit.

Focused regressions cover:

- a strong user preference cannot outrank an eligible candidate that supports a confirmed mandatory weekly minimum;
- a mandatory weekly maximum blocks a matching candidate through Meal Plan-Fit;
- lower-bound uncertainty around a mandatory maximum remains `unknown` and fails closed.

This remains slot-level adaptive selection. Simultaneous combinatorial optimization of the whole week is deferred.

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
8a. Deterministic weekly frequency progress                               DONE (v1, PR #48)
8b. Weekly-aware adaptive candidate selection                             IN PROGRESS
8c. Full-week multi-slot optimization                                     PENDING
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
- full-week combinatorial optimization is deferred;
- shared-Family recommendation does not yet aggregate participant-specific weekly frequency support for group ordering;
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
2. read this file plus ADR-044 and ADR-045;
3. if the weekly-adaptive branch/PR is active, inspect API/Web CI on the exact latest head;
4. verify minimum-support semantics, mandatory-maximum fail-closed behavior and explicit-only candidate classification;
5. verify recommendation ranking consumes Meal Plan-Fit weekly evidence and does not recreate frequency evaluation;
6. guarded squash-merge only after exact-head CI is green and the PR head is unchanged/mergeable;
7. verify post-merge `main` CI;
8. continue toward full-week multi-slot optimization or participant-specific shared-family weekly adaptation without weakening the common evaluator boundary.