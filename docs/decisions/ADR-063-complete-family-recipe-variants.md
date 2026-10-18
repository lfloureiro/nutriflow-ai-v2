# ADR-063 — Complete Family recipe variants

Date: 2026-10-18
Status: implemented and verified locally; pending integration

## Decision

Represent a complete Family variant with `FamilyRecipeVariant` plus an immutable Family
`Recipe` projection containing all effective ingredients. The original remains untouched.
This reuses composition calculation, participant Plan-Fit, recommendation, Servings and
shopping instead of a separate nutrient engine or one copy per Person/meal.

The variant has a lineage/revision, independent concurrency version, draft/active/retired
state, explicit replacement operations and source/variant fingerprints. Each operation
identifies a source ingredient, real replacement FoodItem, whole-recipe amount/unit and
preparation. Confirmed serving count is required; draft creation does not imply activation.
Generic recipe editing/deactivation cannot modify these projections. A changed variant
requires another immutable revision. Activation retires the prior active lineage revision.

## Validation and lifecycle

Draft composition uses current ingredient nutrition. Missing composition, unsafe unit
conversion, missing energy or changed base/ingredient evidence prevent activation.
Validation evaluates the complete projected recipe for each selected Person, date,
meal and portion with existing Plan-Fit/weekly frequency and automatic planning rules.
Activation repeats validation and records its context; it is not a universal clinical
certification. Other people, dates and portions are evaluated again during planning.

Active fresh projections enter the normal catalogue/bootstrap. Original and variant are
evaluated independently: an incompatible original remains blocked; a variant must pass
every present participant's rules. Changed/retired variants are excluded from discovery
and rejected if submitted through a previously loaded candidate. Manual variant planning
also validates participants; existing engine gates still apply to weekly acceptance.

Persisted Servings reference the immutable projected recipe/composition. Shopping therefore
uses effective ingredients, without retaining the originals that were replaced. Retiring
or revising a variant does not rewrite historical Servings or their ingredient projection.
The weekly proposal and saved grid expose all operation summaries.

## Interface

The existing substitution review contains a complete-variant editor, not another primary
menu. Select all required operations and actual catalogue ingredients; enter confirmed
serving count, quantities and preparation; save draft, validate the selected people and
meal, then activate. Validation changes invalidate the displayed result. The weekly wizard
passes its people/date into this editor. A fresh weekly calculation includes activated variants.

## Boundaries

Schema head `58960d47819f`, parent `d7c626668227`. Migration applied locally after backup;
upgrade/downgrade/upgrade tested only on the isolated test database.
This does not supply missing labels, invent FODMAP dose thresholds, activate real Family
variants, implement per-slot attendance or turn retailer observations into lab composition.
The current UI validates one serving per selected person initially; the planner reevaluates
actual portions. Conservative unknown mandatory evidence can block activation.

Per-slot attendance, phase/tolerance controls, richer product/pack linking and unified
delivery/map work remain on `../vision/implementation-task-board.md`.

## Verification

379 API tests and 104 frontend tests passed, plus TypeScript/build, Ruff and schema check.
Browser workflow completed in the isolated database: create two-operation draft, validate,
activate, generate/apply a week and inspect effective shopping and saved portion detail.
See `../audits/2026-10-18/complete-variant-interface-verification.md` for evidence, synthetic
quantities and UI corrections. No real Family variant or meal was activated/applied.
