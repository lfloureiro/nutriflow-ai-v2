# Guided week planning and retail alternatives

## Automatic defaults update — ADR-062

The user's subsequent request supersedes the manual-only defaults below. POST
`/api/families/{family_id}/planning-restrictions` now resolves selected participants'
effective food exclusions and confirmed structured FODMAP diet guidance across the week.
The explicitly configured canonical SIBO condition also activates the requested FODMAP
planning profile while reported/confirmed and within its dates. The UI preselects those
foods and explains person/origin/dates; unmapped active conditions are reported.
Automatic IDs are not saved into manual exclusions and are recomputed per slot on
proposal and acceptance. This update creates no permanent clinical constraint or schema.

Familiar base recipes now show affected ingredients and alternatives immediately,
including all open non-rejected proposals, review status, unresolved quantity and store
options. The weekly grid exposes actual executable swaps and pending changes on existing
unadapted base recipes. The recipe list is searchable and initially limited to six cards.
These cards do not complete multi-operation variants: until quantities/composition and
all participant rules are evaluated, the unchanged incompatible base remains excluded
from executable planning. The SIBO mapping is a Family-requested planning default, not
a claim of a universal clinical diet or indefinite elimination.

Local implementation, 2026-10-18, branch `codex/health-conditions-fodmap-review`.
This increment is not merged. Schema head: `d7c626668227`, parent `3ecd05b9b43a`.

## User journey

Home now exposes **Plan next week**. Primary destinations are Home, Plan, Shopping,
People and Home base; settings/integrations are available through the header gear.
Plan opens a four-step journey: week/people, restrictions, proposal review, shopping.
The default is next calendar Monday and dinners. Existing meals are preserved by the
proposal/materialization engine. The user reviews a proposal before applying it.
Successful application refreshes shopping and opens the selected week's list; a failed
shopping refresh is reported separately from a successfully saved plan.

The current shared generator requires at least two people and uses the same selected
group for the generated slots. Different attendance must still be edited in the agenda.
Per-slot attendance patterns and complete multi-operation recipe variants remain future
work in `../vision/integrated-family-meal-planning-roadmap.md`.

## Persisted setup and explicit exclusions

`FamilyWeekSetup` stores Monday, selected people, meal types and excluded FoodItem IDs.
GET/PUT `/api/families/{family_id}/planning-setup/{week_start}` validates Family scope,
Monday, active ingredients and optimistic `expected_version`; conflicts return 409.
The UI offers ingredient groups linked to the public high-FODMAP educational references.
No exclusion is selected from a diagnosis automatically. Existing personal plan rules
remain effective independently of these additional group choices.

`SharedWeeklyPlanProposalCreate.excluded_food_item_ids` is checked on complete candidate
ingredients after transformation generation, and checked again during materialization.
Opaque dish/product candidates and missing ingredient evidence fail this explicit check.
Accepted events record `requested_group_food_exclusions` in their notes. These criteria
are request choices, not permanent clinical constraints. They do not certify ingredient
compound composition, FODMAP portions, stacking or individual tolerance.

## Retail evidence

`RetailAlternative` stores source URL, observation date, pack size, price observation,
ingredient summary, optional nutrition and evidence tier. Applicable catalogue keys are
explicit. GET `/api/families/{family_id}/retail-alternatives` resolves only visible foods.
`python -m app.retail_alternatives_seed` is explicit and idempotent; no startup scraping.

Four observations imported on 2026-10-18:

| Product | Pack | Observed price | Evidence |
| --- | --- | --- | --- |
| Auchan gluten-free spaghetti | 500 g | €1.75 | Ingredients and nutrition; corn/rice base |
| Continente Rummo gluten-free spaghetti | 400 g | €3.08 | Product description only; full label not imported |
| Auchan lactose-free cooking cream | 200 ml | €0.85 | Ingredients and nutrition; contains milk |
| Continente Agros lactose-free milk | 6 × 1 l | €7.50 | Product description only; full label not imported |

Sources: [Auchan spaghetti](https://www.auchan.pt/pt/biologicos-e-alternativas/sem-gluten/mercearia-sem-gluten/massas-e-farinhas-sem-gluten/massa-auchan-esparguete-sem-gluten-500g/2749257.html),
[Continente spaghetti](https://www.continente.pt/produto/massa-esparguete-sem-gluten-rummo-5884054.html),
[Auchan cream](https://www.auchan.pt/pt/alimentacao/produtos-lacteos/natas-bechamel-e-chantilly/natas/nata-uht-auchan-para-culinaria-sem-lactose-200ml/2945855.html),
[Continente milk](https://www.continente.pt/produto/leite-meio-gordo-sem-lactose-agros-8163556.html).

Candidates appear in restriction guidance, recipe review and relevant shopping lines.
They are suggestions for review; they neither silently change recipes nor create cart
items. Prices and stock are not live. They have no imported laboratory FODMAP serving
approval. Gluten-free labelling alone is insufficient, as explained by the public
[Monash FAQ](https://www.monashfodmap.com/about-fodmap-and-ibs/frequently-asked-questions/).
That educational label-check reference brings the local public reference selection to
23 entries. The licensed Monash database has not been extracted.

## Shopping quantities

Legacy recipes without `serving_count` can use the frozen composition's serving basis
only when recipe identity and every ingredient identity, amount and unit still match.
Transformed servings use the frozen source composition for that check. Missing or stale
evidence keeps the quantity warning; estimated serving counts produce an explicit
approximation warning. This repairs empty shopping calculations without inventing yield.

## Validation

Isolated PostgreSQL migration upgrade and live Alembic check; 359 API tests passed.
Web: 97 tests, TypeScript and production build passed. New tests cover setup concurrency,
Family scope, seed idempotence/evidence, ingredient exclusions on preview/accept,
missing-evidence rejection, and matching/stale snapshot shopping calculations.

Delivery integrations and restaurant map remain as described in ADR-060: no live Uber,
Glovo or Bolt adapter was activated by this increment.

## Produto concreto e embalagens — ADR-069

O rótulo completo pode originar um ingrediente próprio confirmado. Depois de validar
uma variante com esse ingrediente, as compras permitem rever e guardar o número de
embalagens, o excedente e o custo observado. A ligação de proposta ao ingrediente
original não basta para escolher o produto. Dados incompletos continuam bloqueados.
Ver ADR-069 para snapshots, concorrência, alterações que exigem revisão e limitações.
