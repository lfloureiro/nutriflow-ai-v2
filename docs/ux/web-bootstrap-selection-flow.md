# Web bootstrap selection flow

## Goal

Remove technical planning UUID entry from the normal web recommendation workflow while keeping server-authoritative persisted evidence.

## User flow

```text
Family development context
  -> Person
  -> Meal date/time
  -> server planning bootstrap
  -> daily nutrition summary
  -> named Food/Recipe selection
  -> quantity/unit
  -> practical recommendation
  -> accept/reject
```

## Behaviour

Selecting a Person and meal instant triggers the planning bootstrap API. The returned `planning_date` and `DailyNutritionState` are displayed as context rather than editable identifiers. FoodItem and Recipe candidates are shown by human-readable name, optional brand, reference serving and energy.

Composition IDs remain internal. When a candidate is selected, the UI stores the server-selected composition ID and initializes the requested quantity/unit from the returned reference serving. The user may then change quantity/unit before requesting a recommendation.

Changing Person or meal instant invalidates the previous bootstrap, candidate selections, recommendation result and decisions. This avoids silently using evidence selected for another Person or planning instant.

## Missing evidence

If no `DailyNutritionState` exists for the local planning date, the UI explains that state is missing and disables recommendation submission. It does not manufacture or guess a state ID.

If there are no current candidates with valid composition evidence, the UI explains that the catalogue has no usable options for that instant.

## Safety boundary

The web client does not implement allergy, mandatory nutrient, practical availability or ranking rules. It sends the persisted evidence selected by the bootstrap endpoint to the existing practical recommendation API and renders the server result.

## Current limitation

Family selection still uses a UUID development entrypoint. Authentication and explicit household authorization are separate follow-up work.
