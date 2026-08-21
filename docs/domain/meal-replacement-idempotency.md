# Meal replacement and idempotency

## Purpose

Meal planning is exposed to retries, repeated user actions and later edits. NutriFlow must not create duplicate MealEvent records when the same logical request is retried, and it must preserve history when a planned meal is replaced.

This increment adds explicit MealEvent idempotency and replacement semantics before API/UI write endpoints are introduced.

## MealEvent idempotency key

MealEvent now has an optional `idempotency_key`.

The database enforces uniqueness for:

```text
(family_id, idempotency_key)
```

The key is therefore scoped to one Family. The same external key can be reused by another Family without collision.

Null keys remain allowed for historical/manual records that were not created through an idempotent command.

A non-null key must not be empty and is limited to 160 characters.

## Idempotent create semantics

`create_idempotent_meal_event()` receives a complete `MealEventSpec` and an idempotency key.

If no MealEvent exists with that Family/key pair, a new planned event is created.

If the same Family/key pair already exists and the persisted request-defining fields match, the existing event is returned with `created=False`.

If the key already exists but the request payload differs, the service raises `MealIdempotencyConflictError` rather than silently returning or mutating the wrong event.

The comparison covers:

- Family;
- replacement parent, when applicable;
- meal type;
- title;
- scheduled instant;
- timezone;
- location;
- source and source reference;
- notes.

Lifecycle status is deliberately not part of the idempotency comparison. A retry of the original create request should still resolve to the same MealEvent even if that event has subsequently moved from `planned` to another lifecycle state.

## Database uniqueness and concurrency

Application lookup provides normal retry behaviour. The database unique constraint is the final duplicate-prevention boundary.

Two truly concurrent transactions can both perform the initial lookup before either commits. One can then lose the database uniqueness race. A future API transaction boundary should catch that uniqueness conflict, roll back the losing transaction and fetch the already-created Family/key event.

The domain service does not suppress or weaken the database constraint.

## Replacement semantics

`replace_meal_event_plan()` creates a new MealEvent rather than mutating the original planned event in place.

The new event:

- uses a new idempotency key;
- points to the original through `replaces_meal_event_id`;
- starts in `planned` state;
- receives the requested replacement schedule/context fields;
- clones the original person-specific planned content.

The original MealEvent is changed to `replaced` only after the replacement has been constructed.

This keeps the previous plan available for audit and adherence analysis.

## What is cloned

For each original MealParticipant, the replacement creates a new planned MealParticipant for the same Person.

For each planned Serving, the replacement preserves:

- FoodItem/Recipe links;
- exact composition snapshot links;
- item identity snapshots;
- planned quantity and unit;
- planned energy;
- nutrition source and calculation version;
- source reference and notes;
- planned nutrient components.

Served and consumed values are not copied into the replacement plan.

## Safety boundary for replacement

A replacement is a planning operation, not a way to rewrite realized intake.

The service therefore accepts only MealEvents in `planned` or `prepared` state and rejects replacement when:

- the event has `served_at` or `completed_at`;
- a participant is no longer `planned`;
- a Serving is no longer `planned`;
- a Serving already contains served/consumed quantity, energy or consumption timestamp data.

Once food has been served or consumed, corrections should use explicit intake/correction semantics rather than plan replacement.

## Idempotent replacement retries

Replacement is also idempotent.

A retry with the same Family/key and identical replacement specification returns the already-created replacement without cloning another MealEvent.

A different replacement request cannot reuse the same key.

After an event has been replaced, a second replacement with a different idempotency key is rejected by this service. Later workflow requirements can introduce an explicit replacement-chain command if multi-step replanning is needed.

## Interaction with DailyNutritionState

DailyNutritionState recalculation already excludes MealEvents whose status is `replaced`.

Therefore, after replacement:

```text
old MealEvent (replaced) -> excluded from active planned nutrition
new MealEvent (planned)  -> contributes its cloned planned Servings
```

Historical plan data remains available without double-counting current planned nutrition.

## Scope boundary

This increment establishes the persistence and application-service semantics needed by future write APIs.

It does not yet add HTTP endpoints or client retry headers. API vertical slices should map request idempotency tokens into `MealEvent.idempotency_key` and apply the transaction-level uniqueness retry described above.
