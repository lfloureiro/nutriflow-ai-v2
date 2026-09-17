# NutriFlow AI v2 development continuity

This is the authoritative handover entry point for NutriFlow AI v2. Repository code, migrations, tests, domain docs and ADRs take precedence over conversation history.

## Repository checkpoint

Nutrition Plan / Guidance capability blocks:

```text
PR #37  NutritionPlan + EffectiveNutritionPlan foundation                  MERGED
PR #38  reviewed text import / confirmation boundary                       MERGED
PR #39  deterministic Meal Plan-Fit evaluation + focused test UI            MERGED
PR #42  AI-assisted text interpretation + browser review UI                 MERGED
PR #43  Structured Meal Transformation proposals                           MERGED
PR #44  PDF/DOCX/TXT/Markdown text extraction into import review            MERGED
PR #45  scoped single-Person recommendations consume Meal Plan-Fit          MERGED
PR #46  shared-family recommendations use Person-specific Meal Plan-Fit     MERGED
PR #47  restaurant/delivery recommendations consume Meal Plan-Fit           MERGED
PR #48  deterministic weekly frequency progress                            MERGED
PR #49  individual recommendations use weekly frequency progress            MERGED
PR #50  Person-specific weekly support in shared-family ranking             MERGED
8c       full-week multi-slot planning foundation                            IN PROGRESS
```

Confirmed `main` after PR #50:

```text
153af395e2b875763d621ff150e366e4c27a1695
```

Current focused branch, created from that exact main SHA:

```text
feature/full-week-multi-slot-planning-foundation
```

The current slice adds no migration. Repository schema head remains:

```text
d2e6f1a9c4b7
```

Do not treat any SHA in this file as permanently current. At every new session resolve `refs/heads/main`, inspect the open PR and confirm CI on the exact final head before merging or starting new work.

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
-> MealPlanFit for candidate + exact Person-specific portion
-> Person-specific weekly frequency progress
-> weekly-aware MealPlanFit guideline evidence
-> Structured Meal Transformation proposals
-> single-Person / shared-Family / external recommendation paths
-> practical availability + preference + diversity + feedback
-> adaptive candidate ordering from weekly support
-> multi-slot weekly composition over existing Meal Plan-Fit evidence
-> Family MealEvent + Person-specific Servings
```

Authoritative product roadmap: `docs/vision/nutrition-plan-guidance-roadmap.md`.

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
- ADR-046 shared-family weekly support remains Person-specific
- ADR-047 full-week planning consumes Meal Plan-Fit evidence

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
- Mandatory weekly maxima fail closed when remaining safe capacity cannot be established from available structured evidence.
- User preference remains separate from nutrition/practical fit.
- Professional guidance is not silently overridden by lower-authority guidance.
- Conflicts are surfaced, not silently resolved.
- Historical Servings and composition provenance remain stable when catalogue data changes.
- Structured transformations never silently mutate their source Recipe.
- Practical availability, price, family preference, diversity and feedback may rank an eligible meal but may not reverse Meal Plan-Fit ineligibility.
- Shared-family Plan-Fit is Person-specific; one Person's plan or weekly evidence must never be copied to another Person.
- Any hard failure for any shared-meal participant excludes that shared candidate before Family-level ranking.
- External items without persisted composition evidence are not nutrition-ranked.
- Weekly frequency evaluation never classifies food from names/descriptions; only persisted structured planning evidence may count.
- Recommendation and week-planning code consume weekly evidence from Meal Plan-Fit rather than implementing another frequency evaluator.
- Weekly minimum support is ranking/optimization pressure only; it is never an obligation for one meal slot.
- Full-week planning must recheck constraints that can be violated only by the combination of several individually eligible choices.
- Browser code presents server-authoritative nutrition/planning evidence.
- Persisted timezones are valid IANA names.

## Recommendation integration

Single-Person, shared-Family and external restaurant/delivery production recommendation paths consume common Meal Plan-Fit semantics when an explicit meal scope exists.

External restaurant/delivery observations are normalized to ordinary catalogue abstractions:

```text
FoodItem
+ optional versioned FoodCompositionSnapshot
+ MealCandidateAvailability
+ MealCommercialOffer
```

Commercial items without nutrition composition remain visible but unranked. Price/provider/preference cannot override mandatory Plan-Fit failure.

## Phase 8a — weekly frequency progress — DONE v1

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

## Phase 8b — individual weekly-aware candidate selection — DONE v1

PR #49 extended production Meal Plan-Fit with Phase 8a weekly evidence instead of introducing a separate nutrition evaluator.

A candidate matching a confirmed remaining weekly minimum receives `support`. A non-matching candidate is not blocked because later meals can still satisfy the minimum. Mandatory weekly maxima fail or fail closed when structured evidence cannot prove safe capacity. Weekly support remains separate from numeric `fit_score`.

Among already eligible individual candidates, ranking orders confirmed mandatory-minimum support first, then advisory-minimum support, then preserves the previous recommendation ranking.

## Phase 8b extension — shared-Family weekly adaptation — DONE v1

PR #50 keeps every participant's weekly evidence independent:

```text
Person A portion -> Person A Meal Plan-Fit -> Person A guideline_results
Person B portion -> Person B Meal Plan-Fit -> Person B guideline_results
...
-> exclude candidate if ANY Person fails a hard gate
-> aggregate only weekly support evidence for the remaining eligible candidate
-> Family ordering
```

Shared ordering is deterministic:

```text
mandatory-support participant coverage
-> total mandatory support statements
-> advisory-support participant coverage
-> total advisory support statements
-> minimum participant score (fairness)
-> average score
-> candidate key
```

The common weekly recommendation adapter owns interpretation of `guideline_results` into mandatory/advisory support counts. The shared layer only aggregates Person-specific results. Diversity and feedback score adjustments reapply the canonical shared ranking so they cannot erase higher weekly support.

ADR: `docs/decisions/ADR-046-shared-family-weekly-support-is-person-specific.md`.

## Phase 8c — full-week multi-slot optimization — IN PROGRESS

Current branch:

```text
feature/full-week-multi-slot-planning-foundation
```

The foundation composes several already evaluated future meal slots for one Person. It does not introduce another nutrition evaluator or classifier.

Input boundary:

```text
slot
-> CandidateEvaluation
-> MealPlanFitRead
-> structured weekly guideline evidence
```

The first deterministic optimizer slice:

- accepts only candidates already eligible in recommendation and Meal Plan-Fit;
- preserves structured `candidate_matches` evidence from the existing weekly Meal Plan-Fit classifier;
- preserves `unclassified_meal_count` when weekly progress is a lower bound;
- rechecks mandatory weekly maxima over the whole selected combination, including unknown matches conservatively;
- rewards confirmed mandatory weekly minimum deficits before advisory deficits;
- caps support credit at the confirmed remaining deficit so repeated matching meals cannot over-count the target;
- then compares minimum candidate score, average score, exact-repeat count and stable candidate keys;
- refuses search spaces above an explicit deterministic combination limit instead of silently approximating.

This foundation is intentionally one-Person/one-week and in-memory. It adds no migration and no acceptance/persistence API yet.

ADR: `docs/decisions/ADR-047-full-week-planning-consumes-meal-plan-fit-evidence.md`.

Next Phase 8c increments after this foundation include projected daily nutrient composition across several same-day slots, shared-Family multi-slot fairness/portions, richer across-week category/protein diversity, pantry/shopping/schedule coupling and a scalable search strategy.

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
8. Adaptive weekly planning                                               IN PROGRESS
8a. Deterministic weekly frequency progress                               DONE (v1, PR #48)
8b. Individual weekly-aware candidate selection                           DONE (v1, PR #49)
8b extension. Shared-family participant-specific weekly adaptation        DONE (v1, PR #50)
8c. Full-week multi-slot optimization                                     IN PROGRESS
8c foundation. Person-specific multi-slot weekly composition              IN PROGRESS
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
- full-week optimization currently has an explicit exhaustive-search cap;
- projected daily nutrient coupling across several proposed slots is not yet implemented;
- shared-Family multi-slot optimization is not yet implemented;
- pantry depletion, shopping and schedule coupling are not yet optimized jointly;
- richer reviewed food-category taxonomy/equivalence is deferred;
- qualitative guidance remains visible but is not automatically guessed/scored;
- unscoped recommendation still has the legacy nutrition evaluator;
- MealPlanFit still imports private candidate-loading helpers from recommendation API; extract a public common service later;
- candidate-by-candidate Plan-Fit is correct but not yet batch-optimized;
- transformation proposals are not yet persistent Recipe variants;
- production npm lockfile / `npm ci` hardening remains pending.

## Delivery workflow — ADR-007

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

At a new session during this slice:

1. resolve current `main`, branch head, open PR and schema head;
2. confirm branch base is the verified post-PR-#50 main `153af395e2b875763d621ff150e366e4c27a1695` unless main has legitimately advanced;
3. read this file plus ADR-044 through ADR-047;
4. verify the multi-slot planner consumes Meal Plan-Fit evidence and does not classify food independently;
5. verify combinations cannot exceed a mandatory weekly maximum, including lower-bound/unknown evidence;
6. verify minimum-support credit is capped at the confirmed remaining deficit;
7. inspect API CI and Web CI on the exact latest PR head; warnings count as failures;
8. guarded squash-merge only after exact-head CI is green, PR head is unchanged and PR is mergeable;
9. verify post-merge `main` before starting the next Phase 8c increment.
