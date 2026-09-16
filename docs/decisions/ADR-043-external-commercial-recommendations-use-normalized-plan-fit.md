# ADR-043 — External commercial recommendations use normalized persisted evidence and Meal Plan-Fit

## Status

Accepted.

## Context

NutriFlow already supports restaurant/delivery discovery and provider synchronization, and normalizes observed menu items into ordinary `FoodItem`, optional versioned `FoodCompositionSnapshot`, `MealCandidateAvailability` and `MealCommercialOffer` records.

ADR-041 and ADR-042 established Meal Plan-Fit as the authoritative nutrition/safety evaluator for scoped single-Person and shared-family recommendation paths. The remaining risk was to introduce a second nutrition-ranking path specifically for restaurant or delivery providers.

External menu evidence is also inherently uneven. Some items have official/provider nutrition, some have estimates with explicit confidence, and others have no usable composition at all. Missing nutrition evidence must never be converted into zero-valued nutrients simply to make a commercial item rankable.

## Decision

External restaurant/delivery recommendations use the same normalized catalogue and Meal Plan-Fit pipeline as other meal sources.

```text
provider discovery / observed menu
-> normalized persisted FoodItem
-> versioned FoodCompositionSnapshot when nutrition evidence exists
-> MealCandidateAvailability + MealCommercialOffer
-> external recommendation discovery for Person/date/meal
-> explicit evidence classification
-> common practical Meal Plan-Fit evaluator
-> preference / practical context
-> diversity / feedback
-> ranked commercial options
```

### No provider-specific nutrition evaluator

Provider adapters may discover or synchronize external menu data, but they do not decide nutrition eligibility or calculate an independent health score. Once normalized, commercial candidates enter the same server-authoritative Meal Plan-Fit evaluator used elsewhere.

### Persisted normalized evidence is required for nutrition ranking

A commercial item is evaluated nutritionally only when a usable versioned `FoodCompositionSnapshot` exists for the normalized `FoodItem` at the planning instant.

An item without composition evidence remains visible in the external recommendation evidence response with an explicit reason such as `nutrition_composition_missing`, but it is not passed to the nutrition scorer. Missing protein, sodium, energy or other nutrition evidence is therefore not silently treated as zero.

### Evidence provenance remains visible

External composition metadata preserves the normalized evidence class:

```text
official
provider
estimated
```

Estimated evidence may also carry confidence. This metadata is returned with discovery/evaluation evidence so callers can distinguish evidence quality. Evidence confidence does not silently relax mandatory rules; Meal Plan-Fit continues to apply the rules supported by the available normalized composition and fails closed where mandatory evidence/context cannot be evaluated safely.

### Commercial portion semantics

External recommendation v1 evaluates the exact reference quantity/unit stored with the selected commercial composition. Automatic nutrition-driven portion resizing is disabled for these candidates because an observed restaurant/delivery item is a commercial product with a provider-defined portion; NutriFlow must not silently pretend that a different portion is what can actually be ordered.

Future explicit half/double/add-on variants must be represented as concrete commercial candidates or transformations with sufficient evidence.

### Availability and provider filtering

Only normalized external rows with active availability and an active commercial offer at the requested planning instant enter the discovery set. Delivery provider filters are applied before nutrition evaluation.

Commercial price, fees, provider and availability remain practical evidence. They cannot reverse Plan-Fit ineligibility.

### Meal suitability

The external orchestration uses the same persisted/default meal-suitability semantics as normal recommendation candidates. Candidates not suitable for the requested meal are surfaced as not evaluated instead of being force-scored in an invented meal context.

## Consequences

Positive:

- restaurant and delivery use the same NutritionPlan semantics as home/pantry/shared meals;
- provider-specific integration remains replaceable and outside product nutrition logic;
- mandatory professional-plan failures cannot be outweighed by price or preference;
- missing nutrition evidence remains explicit and auditable rather than becoming zero;
- official/provider/estimated provenance remains visible;
- existing practical availability, commercial offers, diversity and feedback layers are reused.

Trade-offs:

- external candidates without composition evidence cannot yet receive a nutrition ranking;
- commercial v1 evaluates the persisted provider portion as-is and does not optimize portion size;
- discovery currently works over already normalized/persisted external items; live provider discovery/sync remains a separate adapter step;
- large external catalogues are capped before Plan-Fit evaluation and will need better preselection/search as provider coverage grows.

## Follow-up

- connect live restaurant/delivery discovery adapters to this persisted-normalization boundary without bypassing it;
- add richer evidence-quality presentation in the frontend;
- support explicit commercial variants/add-ons/portion options when provider evidence supports them;
- add location/search preselection before the bounded candidate set for large catalogues;
- keep external recommendation explanations tied to the exact persisted composition and commercial offer provenance.
