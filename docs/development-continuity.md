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
Phase 7 external restaurant/delivery Plan-Fit                             IN PROGRESS
```

Confirmed `main` after PR #46 and before the current Phase 7 branch:

```text
19534a2bcf0c332666386a8257b8a249261a4506
```

Current Phase 7 branch:

```text
feature/external-meal-recommendations-plan-fit
```

PR #45, PR #46 and the current Phase 7 slice add no migration. Verified migration chain remains:

```text
c1f4a8d2e6b9 -> d2e6f1a9c4b7
```

with `d2e6f1a9c4b7` (`add_food_transformation_profiles`) as the repository schema head at this checkpoint.

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
-> single-Person or shared-family recommendation eligibility/fit
-> practical availability + preference + diversity + feedback
-> Family meal planning / Person-specific Servings
-> pantry / shopping
-> normalized restaurant / delivery catalogue evidence
-> external commercial recommendation through the same Meal Plan-Fit path
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
- Practical availability, price, family preference, diversity and feedback may rank an eligible meal but may not reverse Meal Plan-Fit ineligibility.
- If Plan-Fit is eligible but numerically unscored, missing score is omitted rather than converted to zero.
- Shared-family Plan-Fit is Person-specific; one Person's plan must never be copied to another Person.
- A shared candidate is eligible only when every participant is eligible for their own final portion.
- Provider-specific discovery/sync remains outside the common nutrition evaluator.
- External items without persisted composition evidence are not nutrition-ranked and are never converted to zero-valued nutrition.
- Browser code presents server-authoritative nutrition/planning evidence.
- Demo/synthetic evidence remains explicitly development-only.
- Persisted timezones are valid IANA names.

## Nutrition Plan and Plan-Fit chain

### Plan ingestion

The ingestion path is:

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

### Meal Plan-Fit

`POST /api/persons/{person_id}/meal-plan-fit` evaluates EffectiveNutritionPlan against exact candidate composition/portion evidence.

Important semantics:

- meal-scoped numeric rules evaluated directly;
- daily rules evaluated against DailyNutritionState projected totals;
- mandatory conflicts/safety/evidence failures are hard gates;
- qualitative/frequency guidance is visible but not guessed/scored;
- fit score is secondary and cannot override eligibility.

### Structured Meal Transformation

The current transformation flow is:

```text
Recipe + portion
-> baseline MealPlanFit
-> explicit same-group ingredient alternatives
-> explicit portion-equivalence metadata
-> virtual replacement nutrition
-> after MealPlanFit
-> only demonstrably improving proposals
```

The source Recipe is never silently mutated. Persistent variants and multi-operation/cooking-method transformations remain deferred.

## Recommendation integration

### PR #45 — scoped single-Person recommendation

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

This covers basic scoped recommendations and the practical home/pantry/commercial recommendation endpoint. Optional portion sizing happens before Plan-Fit. Recommendation calls without `meal_type` intentionally retain the legacy evaluator until a safe explicit scope exists.

### PR #46 — shared-family recommendation

Production shared-practical recommendations evaluate:

```text
Person × candidate × final Person-specific portion
-> that Person's EffectiveNutritionPlan + DailyNutritionState
-> Meal Plan-Fit
-> Person-specific preference/practical context
-> shared eligibility aggregation
-> minimum participant score before average participant score
-> diversity
-> feedback
```

A mandatory failure for one participant blocks the shared candidate and retains the Person id in exclusion reasons. Another participant's score or preference cannot average the failure away.

The lower-level legacy `shared_family_meal.py` evaluator remains temporarily available for direct legacy/unit-test callers; the production shared-practical API uses `shared_family_meal_plan_fit.py`.

### Phase 7 — restaurant/delivery recommendation (current branch)

Existing provider/observed-menu ingestion already normalizes external food to:

```text
FoodItem
+ optional versioned FoodCompositionSnapshot
+ MealCandidateAvailability
+ MealCommercialOffer
```

Current branch adds an external recommendation orchestration endpoint conceptually equivalent to:

```text
POST /api/persons/{person_id}/meal-recommendations/external
```

The intended/current implementation path is:

```text
normalized active restaurant/delivery catalogue
-> Person + planning instant + meal type
-> active commercial/provider filtering
-> latest persisted composition evidence
-> explicit evidence classification
-> exact provider/composition reference portion
-> common practical Meal Plan-Fit pipeline
-> preference/practical context
-> diversity/feedback
-> ranked commercial options
```

Important Phase 7 rules:

- no provider-specific nutrition score;
- only persisted normalized composition evidence enters nutrition ranking;
- external rows without composition remain visible as `nutrition_composition_missing` and are not scored;
- evidence level (`official`, `provider`, `estimated`) and confidence remain visible;
- commercial portions are not auto-resized in v1;
- active offer/provider filtering occurs before scoring;
- mandatory Plan-Fit failure cannot be reversed by lower price or user preference.

Focused tests cover a cheaper/user-preferred low-protein delivery item remaining blocked by a mandatory professional lunch protein rule while a higher-protein item remains eligible, and a no-nutrition commercial item remaining explicitly unranked.

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
- provider discovery/synchronization adapters;
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

Nutrition Plan, plan import, document upload, Plan-Fit and transformation proposals live under the selected Person's Nutrition context; meal planning and operational recommendations remain under Refeições.

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
7. Restaurant/delivery recommendations consuming same Plan-Fit             IN PROGRESS
8. Weekly adaptive planning + frequency progress                           PENDING
9. Feedback/learning refinement                                            PENDING
```

OCR/photo import remains a parallel capability gap, not a reason to create a second plan-import trust boundary.

## Known limitations / technical debt

- production authentication / Family authorization are not implemented;
- Family UUID remains development context;
- purchased ShoppingListItem does not automatically create PantryStockLot;
- catalogue evidence quality is incomplete and remains visible;
- consumer marketplace discovery depends on provider access/configuration;
- external recommendation currently depends on already normalized/persisted provider evidence; live discovery and normalization remain separate adapter steps;
- external items without composition are visible but intentionally unranked;
- commercial automatic portion optimization is intentionally disabled in Phase 7 v1;
- OCR/photo/scanned-PDF extraction is deferred;
- weekly frequency progress is deferred;
- qualitative/frequency automatic Plan-Fit evaluation is deferred;
- unscoped recommendation still has the legacy nutrition evaluator;
- lower-level legacy shared-family evaluator remains for direct legacy callers;
- MealPlanFit still imports private candidate-loading helpers from recommendation API; move these to a public common service later;
- shared Plan-Fit service currently imports private aggregation helpers from the legacy shared service; extract public common helpers later;
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
3. if the Phase 7 external recommendation PR/branch is active, inspect API/Web CI on the exact latest head and fix warnings/tests before merge;
4. verify that missing external nutrition evidence stays explicitly unranked and that provider/price/preference cannot override mandatory Plan-Fit failures;
5. guarded squash-merge only after exact-head CI is green and the PR head is unchanged/mergeable;
6. verify post-merge `main` CI;
7. then continue toward weekly frequency/adaptive planning or the next explicit external-provider/frontend integration slice without creating another nutrition evaluator.
