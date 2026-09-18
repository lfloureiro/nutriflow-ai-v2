# Weekly planning smoke test

Use this after changing the Week matrix, weekly proposal generation, or weekly slot materialization.

## Setup

1. Checkout `feature/weekly-proposal-preview-ui`.
2. Start API and web.
3. Open a Family with at least two Persons.
4. Open **Refeições -> Semana**.

## Proposal generation

1. Click **Gerar proposta**.
2. Confirm the UI moves through **A preparar opções…** and **A optimizar semana…**.
3. Existing planned cells must stay unchanged.
4. Proposal generation itself must not create MealEvents.
5. Exact/bounded search status must be visible after the response.

## Matrix and drill-down

Confirm the week shows Monday-Sunday and all four slots:

- Pequeno-almoço
- Almoço
- Lanche
- Jantar

Then:

1. select a day;
2. select a proposed meal;
3. confirm Person-specific quantity and energy are shown when known;
4. confirm existing planned meals remain editable through the normal meal editor.

## Adapted recipes

When the server selects a transformed recipe:

1. the matrix cell must show **Adaptada ao plano** or **Variante por preferência**;
2. meal detail must show the structured substitution, for example `Iogurte natural → Iogurte grego`;
3. the UI must not claim a transformation when `choice.transformation` is null.

## Accept and persistence

### Base recipe

1. Select a normal recipe proposal.
2. Click **Aceitar e guardar**.
3. The server must recompute the whole weekly proposal.
4. The accepted `candidate_key` must still match the reviewed choice.
5. The cell must become **Planeada** after the refreshed Family meal plan is returned.

### Adapted recipe

1. Select a proposal marked **Adaptada ao plano**.
2. Click **Aceitar e guardar**.
3. The browser must send only the reviewed base candidate identity plus the structured ingredient/replacement IDs.
4. The server must recompute the weekly proposal and revalidate the transformation again before persistence.
5. The resulting meal must persist a `MealTransformationApplication`.
6. Person servings must use transformed nutrition provenance, not the original RecipeCompositionSnapshot.
7. If the selected replacement changed between preview and acceptance, expect HTTP 409; never materialize a different adaptation silently.

## Reject

Reject currently excludes the **whole base recipe** for that slot in the current browser review session. This also excludes its transformation variants.

1. Select a proposed meal.
2. Click **Recusar receita e procurar alternativa**.
3. If another feasible recipe exists, the slot should be recalculated to that recipe.
4. Rejection is session-local; it is not yet durable feedback.

## Current source policy

- Breakfast/snack: home catalogue.
- Weekday dinner: home/Family recipes.
- Weekday lunch: delivery-backed candidates only in this UI slice; if there is no structured candidate evidence the slot may remain pending.
- Weekend lunch/dinner: home candidates plus restaurant context; restaurant discovery alone is not treated as a nutrition-ranked dish.
- Leftovers are never invented from the previous dinner without explicit persisted surplus evidence.

## Regression stop conditions

Stop before merge if any of the following occurs:

- a mandatory Plan-Fit failure is ignored;
- missing safety-relevant evidence is treated as zero/pass;
- an existing planned meal is overwritten;
- accepting a base recipe materializes a transformed variant, or vice versa;
- accepting one transformation materializes a different replacement;
- transformed servings claim the original composition snapshot as their nutrition source;
- a rejected base recipe immediately reappears in the same slot;
- breakfast or snack disappears from the weekly flow;
- the UI labels a meal as leftovers without explicit quantity evidence.
