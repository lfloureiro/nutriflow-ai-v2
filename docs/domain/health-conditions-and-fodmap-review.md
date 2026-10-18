# Health conditions and family recipe substitution review

Implemented on `codex/health-conditions-fodmap-review`, stacked on weekly comparison review head `9823b4d716e34b0829b6b57ff3732c46d5bc156c`. Schema head: `3ecd05b9b43a`.

## Person health history

`PersonHealthCondition` belongs to one Person. A stable local code identifies a condition; this is not an ICD/SNOMED claim. The display name, reported/suspected/confirmed/resolved status, source/reference, optional known start/end dates and notes are explicit inputs. Recording a condition creates no NutritionConstraint, FoodAdverseReaction or NutritionPlan.

Professional/document provenance requires a reference. User-reported information cannot be saved as professional confirmation. The software records supplied provenance; it does not authenticate a clinician or verify the diagnosis.

Every create/update appends a `PersonHealthConditionEvent` containing the full snapshot and version. Updates require `expected_version` and reject stale writes with 409. Codes cannot be renamed after creation. Resolve a condition through a new revision; there is no delete endpoint that removes history.

Routes under `/api/families/{family_id}/persons/{person_id}/conditions`:

- GET: list this Person's conditions;
- POST: record a condition;
- PUT `/{condition_id}`: revise it with expected version;
- GET `/{condition_id}/history`: retrieve snapshots, latest first.

All routes validate the Person's Family and ownership of the condition. This is data scoping, not authentication. The application's pre-existing development Family-ID entrypoint remains; production identity, authorization and consent are not implemented by this increment. Do not expose this local development installation publicly as a clinical record system.

Web: `Pessoas → pessoa → Saúde`, including add/edit/status changes and per-condition history. Portuguese/English labels; source notes remain in their original language.

## Public FODMAP reference import

The explicit command imports a curated **22-item educational selection**, not a full laboratory database:

```powershell
cd apps/api
python -m app.fodmap_guidance_seed --family-id <family UUID>
```

The import is never run automatically on startup or as part of the migration. Public guidance is global; proposals are Family-scoped. Re-import skips existing reference/link/proposal identities and preserves reviewed/rejected statuses and edited review notes.

Sources checked on 18 October 2026:

- [Monash public food guidance](https://www.monashfodmap.com/about-fodmap-and-ibs/high-and-low-fodmap-foods/): selected general food categories and reported FODMAP groups.
- [Monash onion/garlic cooking guidance](https://www.monashfodmap.com/blog/cooking-with-onion-and-garlic-myths-and/): selected aromatic alternatives and preparation caveats.
- [Monash application help](https://www.monashfodmap.com/get-app-help/): detailed tested-food database is available through its application; not imported here.
- [Monash calculator terms](https://monashfodmapcalculator.com.au/terms): calculator data must not be extracted/distributed under the published terms; no calculator extraction was attempted.
- [FODMAP Friendly testing](https://fodmapfriendly.com/ingredient-testing/): independently laboratory-tested reference provider, linked in the UI for further access investigation. Its database was not imported.

`FodmapReference` records PT/EN names, a general high/low category, reported groups, source URL/name/version, retrieval date, evidence kind and limitations. These records contain **no quantitative serving limits or laboratory concentrations**. An empty group list is unspecified, not zero. Lower content in general guidance is never a per-person suitability guarantee.

`FoodFodmapReference` uses a curated explicit catalogue-key mapping for category associations. No runtime name inference is used. The mapping basis states that exact product, preparation and dose remain unverified. For example generic yogurt guidance is not a laboratory result for a particular Greek yogurt; a leek category does not distinguish all parts; conserved beans may differ from other preparations. Conflicting evidence should be preserved, not averaged into a safety conclusion.

Future licensed or otherwise authorized detailed imports need their own adapter, provenance/version and preparation/dose model. Do not enter guessed grams or convert public traffic-light classifications into measured concentrations. Revalidation/refresh of a source version is future work: this fixed import preserves existing rows instead of silently replacing historical evidence.

## Recipe substitution review

Web: `Casa → Substituições`, with recipe search, original ingredient quantities, linked public references, suggested alternatives, editable review notes/status, custom alternative proposals and a sources/data tab. Counts are server-backed. Recipe details always remain `not_evaluated` for suitability.

GET `/api/families/{family_id}/recipe-adaptations` returns all active global/Family recipes, their ingredients, linked educational evidence and that Family's review proposals. An empty ingredient list is explicit missing composition. A missing reference means unknown, never low content.

POST to the same path creates a `RecipeSubstitutionReview`. PUT `/{proposal_id}` revises review notes/status with expected version. Cross-Family recipes, replacements and proposal access are rejected. A replacement may be a text idea pending catalogue authoring or reference an existing visible FoodItem. If an amount is proposed, both amount and unit are required; no automatic equivalence is inferred.

States are `proposed`, `reviewed` and `rejected`. Reviewed means organizational review only: it does not certify clinical suitability and does not apply the operation. Proposal review notes/status are mutable with optimistic concurrency; unlike condition revisions, this increment does not retain a separate event history of each proposal edit.

The import proposes reference-backed alternatives where the public guide supports them. It also stores clearly labelled **editorial cooking ideas without a tested-food reference**, including broth/seasoning, cream, thickener and opaque prepared-food review. These are not imported laboratory findings. The seed only proposes replacements; it never writes Recipe, RecipeIngredient, composition snapshots, MealEvents, Servings or shopping lists.

There are no hard gates based on a recorded disease or these educational categories. Existing recommendation and Plan-Fit behavior is unchanged. A future user/professionally defined protocol must activate explicit supported constraints and an evaluator before planning can claim it checked dietary compatibility.

## Next stage: adapt shared family recipes

The detailed next-work sequence is now `docs/vision/integrated-family-meal-planning-roadmap.md`
and ADR-060: attendance by meal, usable explicit restrictions, complete Family variants,
automatic selection for those present and unified source discovery/map. This is planned work;
the implemented review UI still does not activate/apply alternatives.

1. Review the relevant Person's received dietary guidance, tolerances and intended protocol phase; keep it separate from the condition record.
2. Confirm exact brands/labels, food parts/preparation, recipe yield and per-Person quantities. Resolve opaque compounds and missing ingredient lists first.
3. Review all substitutions needed by one recipe together: replacing garlic alone cannot solve a mandatory onion exclusion that remains in the dish.
4. Extend the existing structured transformation flow to a complete ordered operation set, preserving composition provenance and evaluating the final result for every participant.
5. Revalidate supported hard rules on acceptance, then update the planned variant and derived shopping requirements. Do not rewrite consumed-serving history or mutate the global source recipe without an explicit catalogue editing decision.

Suggested review order: aromatics and hidden ingredients in broths/seasonings; exact milk/cream products; wheat-based pasta/thickeners; species/preparation/portion of legumes and mushrooms; complex prepared foods and mixed breakfast products. Garlic-infused oil is part of the oil allocation, not a gram-for-gram replacement for garlic. Removing onion/garlic after simmering in water does not remove what has dissolved into that liquid. [Monash preparation guidance](https://www.monashfodmap.com/blog/cooking-with-onion-and-garlic-myths-and/).

## Validation and local operation

- Migration upgrade/downgrade/upgrade checked on the isolated `nutriflow_review_test` database.
- Alembic check: no additional operations on test and Family databases.
- API Ruff clean; 349 API tests passed with warnings treated as errors, including 11 new tests of history, stale writes, scope, validation, import idempotency and unchanged recipes.
- Web: 92 tests, strict TypeScript and production build passed.
- Browser smoke check: existing Family selection, Person Health condition/history, recipe alternatives and source disclosures.
- Local Family DB: migration applied after a binary pg_dump backup, 22 references and 130 Family proposal rows imported. Existing 66 recipes, 446 ingredient rows, 34 MealEvents and 96 Servings retained. One requested user-reported condition was registered separately through the service; personal identifiers are not embedded in migration/seed code.
- Backup: local `backups/pre-health-conditions-2026-10-18.dump`; never publish database backups or personal audit exports in a public PR.

Local API and Vite run on loopback ports 8000 and 5173. The v2 database was recreated with the existing `nutriflow-ai-v2_nutriflow_postgres_data` volume to restore its configured host port; no volumes were deleted and the v1 was not modified.
