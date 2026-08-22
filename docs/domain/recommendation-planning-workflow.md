# Recommendation planning workflow

The normal Family recommendation UI is a product workflow, not an engine-debug form.

## User flow

```text
Recomendar
-> Pessoas: uma | várias | todas
-> Período: 1 dia | vários dias
-> Dia or De/Até (maximum 14 days)
-> Tipo de refeição: breakfast | lunch | snack | dinner
-> Onde procurar (multi-select):
   - Refeições cozinhadas
   - Encomenda
   - Restaurante
-> Obter recomendações
-> results grouped by day
-> accept one option into that day's meal plan
```

Person selection is a visible multi-select rather than a single-person dropdown. `Todos` selects or clears the complete Family in one action.

When exactly one Person is selected, the existing Person practical recommendation workflow is used.

When two or more Persons are selected, the server uses the shared-Family recommendation domain:

- every selected Person receives an independent nutrition/safety/preference evaluation;
- a candidate is eligible for the group only when it is eligible for every selected Person;
- a mandatory rule for any one selected Person excludes that candidate from the shared recommendation;
- eligible shared candidates rank by the lowest participant score first, then by the average participant score, so a meal that is very poor for one member is not hidden by a high average;
- the response retains participant-specific quantities, nutrition and scores;
- accepting a shared recommendation creates one shared MealEvent with one MealParticipant and Serving per selected Person.

The three source choices are intentionally product-level labels. Internal availability channels remain implementation details:

- `Refeições cozinhadas` maps to the `home` channel and uses active Family Recipe candidates;
- `Encomenda` maps to `delivery` and uses meal-like FoodItem (`dish`) candidates with matching commercial offers;
- `Restaurante` maps to `restaurant` and uses meal-like FoodItem (`dish`) candidates with matching commercial offers.

Sources are OR-combinable. The user can request any one source, any pair, or all three.

`pantry` and `store` remain internal/secondary availability concepts and are no longer exposed as top-level choices in the normal recommendation screen.

## Candidate selection

The normal UI no longer asks the user to manually build candidate rows or enter candidate quantity/unit. Those are engine inputs, not planning decisions.

Candidates are built automatically from the planning bootstrap:

- active Recipe composition snapshots for cooked-meal recommendations;
- active `dish` FoodItem composition snapshots for delivery/restaurant recommendations;
- reference quantity/unit from the authoritative composition snapshot is used as the recommendation input evidence;
- the request remains capped at the backend maximum of 100 candidates.

Commercial-only results are displayed only when there is a matching offer for the requested commercial source. This prevents source-unknown catalogue dishes from being presented to the user as if they were currently orderable.

## Multi-day recommendations

Recommendations remain daily. The web workflow orchestrates one recommendation for each selected date and groups results by day.

For one selected Person this is one Person recommendation run per day. For multiple selected Persons this is one shared-Family evaluation per day, internally evaluating every selected Person against that day's own nutrition state.

Recommendation bootstrap requests use `ensure_state=true`. When a selected day has no DailyNutritionState yet, the server materializes one from that Person's Servings and the active NutritionTarget when available. This makes future planning dates usable without requiring a separate manual state-generation step.

The ordinary planning-bootstrap read remains non-mutating by default (`ensure_state=false`) for backward compatibility.

## Fixed meal type

The recommendation screen uses the same shared four-type contract as the Family meal planner:

```text
breakfast
lunch
snack
dinner
```

Meal type is always selected from a dropdown; arbitrary text is not accepted in the normal UI.

## Progressive disclosure

Primary screen fields are deliberately limited to:

- people;
- period;
- meal type;
- sources.

Time, location and available preparation time are under `Mais opções`. Candidate composition IDs, engine source channels, quantities and units are not normal-user controls.
