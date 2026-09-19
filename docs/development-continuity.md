# NutriFlow AI v2 development continuity

This is the authoritative handover entry point for NutriFlow AI v2. Repository code, migrations, tests, domain docs and ADRs take precedence over conversation history.

## Repository checkpoint

Nutrition Plan / Guidance capability blocks:

```text
PR #37  NutritionPlan + EffectiveNutritionPlan foundation                  MERGED
PR #38  reviewed text import / confirmation boundary                       MERGED
PR #39  deterministic Meal Plan-Fit evaluation + focused test UI           MERGED
PR #42  AI-assisted text interpretation + browser review UI                MERGED
PR #43  Structured Meal Transformation proposals                           MERGED
PR #44  PDF/DOCX/TXT/Markdown text extraction into import review           MERGED
PR #45  scoped single-Person recommendations consume Meal Plan-Fit          MERGED
PR #46  shared-family recommendations use Person-specific Meal Plan-Fit     MERGED
PR #47  restaurant/delivery recommendations consume Meal Plan-Fit           MERGED
PR #48  deterministic weekly frequency progress                            MERGED
PR #49  individual recommendations use weekly frequency progress           MERGED
PR #50  Person-specific weekly support in shared-family ranking             MERGED
PR #51  full-week multi-slot planning foundation                            MERGED
PR #52  same-day daily nutrient coupling                                    MERGED
PR #53  shared-Family multi-slot planning                                   MERGED
PR #54  server-authoritative weekly planning proposal API                   MERGED
PR #55  bounded/scalable weekly search                                      MERGED
PR #59  NutritionPlan authority across Plan-Fit                             MERGED
PR #60  shared-Family recipe transformation evaluation                      MERGED
PR #61  NutritionPlan authority UI                                          MERGED
PR #62  recommendation authority UI                                         MERGED
PR #63  Family transformation preview in recommendations                    MERGED
PR #64  materialized shared recipe transformations                          MERGED
PR #66  weekly planning selects safe recipe adaptations                     MERGED
PR #67  atomic weekly plan materialization                                  MERGED
PR #68  current Week-view frontend                                          MERGED
PR #69  persisted transformed meals in Family planning                      MERGED
current weekly plan -> shopping-list refresh + transformed shopping         IN PROGRESS
```

Confirmed `main` before the current branch:

```text
2d93327a169d691fe4dd5f566da94603ac09a406
```

Current focused branch, created from that exact main SHA:

```text
feature/week-shopping-list-refresh
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
-> same-day recomposition of mandatory daily nutrient upper bounds
-> shared-Family multi-slot composition by reusing each Person's weekly projection
-> server-authoritative weekly proposal API
-> explicit weekly acceptance/materialization boundary
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
- ADR-048 weekly planning rechecks daily nutrient limits across same-day slots
- ADR-049 shared-family weekly planning reuses Person-specific weekly planning
- ADR-050 weekly planning API is server-authoritative

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
- Same-day daily nutrient coupling consumes structured Meal Plan-Fit rule evidence; it does not reload/reinterpret NutritionPlan rules or silently convert units.
- Shared-Family multi-slot planning must project the shared choice through every Person's exact participant evaluation and Plan-Fit before Family aggregation.
- Support for one Person can never rescue a weekly or daily hard failure for another Person.
- Weekly planning clients submit ordinary planning inputs; Plan-Fit and recommendation evidence remain server-authoritative.
- Proposal generation must not silently create MealEvents; weekly acceptance is an explicit later action.
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

PR #51 merged the deterministic one-Person/one-week foundation. PR #52 extended it with same-day recomposition of mandatory nutrient upper bounds. PR #53 added shared-Family multi-slot planning while reusing every Person's existing weekly optimizer.

Person-level input boundary:

```text
slot
-> CandidateEvaluation
-> MealPlanFitRead
-> structured rule/guideline evidence
```

The merged Person planner:

- accepts only candidates already eligible in recommendation and Meal Plan-Fit;
- preserves structured weekly classification evidence and lower-bound uncertainty;
- rechecks mandatory weekly maxima over the whole selected combination;
- rewards confirmed mandatory weekly minimum deficits before advisory deficits;
- caps minimum-support credit at confirmed remaining deficit;
- recomposes mandatory same-day nutrient upper bounds against the common DailyNutritionState baseline;
- keeps daily coupling isolated per date;
- compares minimum candidate score, average score, exact-repeat count and stable candidate keys;
- refuses search spaces above an explicit deterministic combination limit.

The merged shared-Family planner keeps one participant evaluation and one Meal Plan-Fit per Person. For each proposed shared combination it projects the selected shared meals into one singleton-candidate weekly plan per Person and calls the existing Person optimizer. The shared combination is feasible only when every Person projection is feasible.

Family ordering among feasible combinations is:

```text
mandatory-support participant coverage
-> total mandatory supported occurrences
-> advisory-support participant coverage
-> total advisory supported occurrences
-> diversity-adjusted minimum participant score
-> diversity-adjusted average participant score
-> repeated shared-candidate count
-> stable candidate-key sequence
```

Exact recipe repetition inside the proposed week is a soft diversity cost, not a hard gate. Each occurrence beyond the first subtracts 0.25 from the plan-level minimum and average ranking scores. Mandatory/advisory weekly support remains ahead of that adjustment, and clearly worse alternatives can still lose to a repeated favourite. The bounded search applies the same repeat-aware score hint before pruning so approximate search does not systematically collapse onto the same top-ranked recipe.

Current increment: couple an explicitly applied weekly plan to the existing durable shopping-list workflow without weakening weekly-plan atomicity.

The browser submits Family, Persons, ordinary slot/candidate identities and practical context. The server runs the established shared practical recommendation pipeline independently for each slot, carries the exact Person-specific Plan-Fit used for that candidate as transient internal evidence, then feeds the shared weekly optimizer. Clients never submit or own `MealPlanFitRead`, weekly progress, rule evaluation or classification evidence.

Proposal generation returns the selected combination, Person-specific portions/scores/explanations, optimization counters and each slot's recommendation engine version. A requested slot that has no server-authoritative eligible candidate is returned as an explicit pending/skipped slot and is excluded from combination search, so missing live delivery evidence cannot invalidate the rest of the week. It does not create MealEvents. Weekly acceptance/materialization is now explicit and atomic over the selected choices: the server recomputes the reviewed selection, validates candidate/transformation identity and persists all selected MealEvents in one transaction. The Week view refreshes the authoritative meal plan afterwards.

The current branch adds a derivative post-apply shopping refresh. It reuses the existing server-authoritative pantry/shopping calculation, and transformed meals contribute their persisted replacement ingredient rather than the source Recipe ingredient. Shopping refresh failure is reported separately and never implies that an already-committed weekly plan was rolled back.

ADRs:

- `docs/decisions/ADR-047-full-week-planning-consumes-meal-plan-fit-evidence.md`
- `docs/decisions/ADR-048-weekly-planning-rechecks-daily-nutrient-limits.md`
- `docs/decisions/ADR-049-shared-family-weekly-planning-reuses-person-planner.md`
- `docs/decisions/ADR-050-weekly-planning-api-is-server-authoritative.md`
- `docs/decisions/ADR-058-weekly-exact-repeat-diversity-is-soft.md`

Next Phase 8c increments after this slice include proposal acceptance/materialization, richer across-week category/protein diversity, pantry/shopping/schedule coupling and scalable search.

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
8c foundation. Person-specific multi-slot weekly composition              DONE (v1, PR #51)
8c daily coupling. Same-day mandatory nutrient upper bounds               DONE (v1, PR #52)
8c shared. Shared-Family multi-slot Person-specific planning              DONE (v1, PR #53)
8c API. Server-authoritative weekly planning proposal orchestration       DONE (v1, PR #54)
8c search. Deterministic bounded search                                   DONE (v1, PR #55)
8c transformations. Safe transformed variants in weekly planning          DONE (v1, PR #66)
8c materialization. Atomic weekly application                             DONE (v1, PR #67)
8c Week UI. Monday-Sunday progressive-disclosure workflow                 DONE (v1, PR #68)
8c transformed read model. Persisted operation visible after apply        DONE (v1, PR #69)
8c shopping coupling. Refresh pantry-aware shopping after apply           IN PROGRESS
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
- bounded weekly search is deterministic but can still prune the full combinatorial space;
- daily minimum completion is not forced unless complete-day slot coverage becomes explicit;
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
2. confirm branch base is the verified post-PR-#53 main `70d0d344e1b0bc87233b27e88cf94088fb5d9857` unless main has legitimately advanced;
3. read this file plus ADR-044 through ADR-050;
4. verify clients submit only ordinary slot/candidate/practical inputs and never Plan-Fit or weekly progress evidence;
5. verify each shared participant retains the exact server-generated Person-specific Plan-Fit used for that candidate;
6. verify diversity/feedback adjustments preserve that transient Plan-Fit evidence;
7. verify weekly proposal generation calls the shared weekly optimizer and does not create MealEvents;
8. inspect API CI and Web CI on the exact latest PR head; warnings count as failures;
9. guarded squash-merge only after exact-head CI is green, PR head is unchanged and PR is mergeable;
10. verify post-merge `main` before starting weekly proposal acceptance/materialization.


## Review increment — NutritionPlan actionability diagnostics

Temporary review branch:

```text
fix/nutrition-plan-actionability-review
```

Base: exact PR #73 review head `723213cba0721d7b5eaae6c3e58057ca72c8a44c`. This is intentionally stacked on the unmerged integrated review branch because the affected weekly/import code is not yet on `main`. Do not merge this branch or PR #73 without explicit user review.

Confirmed production-like diagnosis from the local Loureiro data:

- Luís has an active `Plano do nutricionista` from 2026-09-18 with 40 rules and 32 guidelines;
- the effective plan for 2026-09-21 dinner reports `active_plan`;
- Mac and Cheese is `eligible=True`, `status=unknown`, `fit_score=None`, with candidate authority `partial_plan_coverage`;
- the plan is therefore persisted and loaded correctly; the apparent absence in Week UI came from downstream response loss plus unsupported rule evidence.

This increment:

- propagates Person-specific `plan_fit_status`, `plan_fit_score`, `nutrition_plan_authority`, active plan IDs/titles and unknown evidence into weekly proposal participants;
- shows the derived authority in the Week detail instead of presenting raw `unknown` as if no plan existed;
- allows explicit prohibitions to use the existing import `numeric_rule` envelope with `operator=exclude` and no numeric values/unit;
- materializes confirmed exclusions as `NutritionConstraint(constraint_type=exclusion)`;
- teaches ChatGPT-assisted import to split explicit multi-subject exclusions while preserving review/provenance;
- keeps unsupported food-category evidence unknown/not evaluated and never infers membership from recipe names/descriptions.

No database migration is introduced by this increment.

Before opening any PR, run the ADR-007 local gates on the exact branch head:

```powershell
python -m alembic check
cd apps\api
python -m ruff check .
python -m pytest -q

cd ..\web
npm install --no-package-lock --ignore-scripts
npm run test
npm run build
```

Only after those local gates are explicitly green should an integration/review PR be opened.


## Review regression fix — legacy Recipe serving normalization

Stacked review branch:

```text
fix/legacy-recipe-serving-normalization-review
```

Base: NutritionPlan actionability review head `31c5bca37b55bdf6f81e7bde55c9ade9246e7a72`.

During functional review, Mac and Cheese exposed an independent portion-sizing defect: its legacy RecipeCompositionSnapshot represented the whole recipe as `6 serving` / `5899 kcal`, while `Recipe.serving_count` was null. Planning bootstrap therefore exposed 6 servings as the candidate baseline, and automatic portion sizing could only scale that baseline by 0.5x..2x, producing impossible Person portions such as 3 or 6 servings.

The bootstrap now treats a composition whose `reference_unit=serving` as intrinsically scalable by serving count: the planning candidate baseline is 1 serving and energy is scaled by `1 / reference_quantity`. This does not mutate legacy Recipe rows or infer a missing serving_count. Non-serving snapshots retain the existing serving_count/yield behaviour.

Regression coverage includes the real legacy shape `6 serving / 5899 kcal / serving_count=None`.
