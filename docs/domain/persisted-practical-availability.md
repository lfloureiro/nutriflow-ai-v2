# Persisted practical meal availability

NutriFlow uses durable Family-scoped operational data rather than relying only on request-local `CandidatePracticalProfile` objects. `MealCandidateAvailability` is the stable source identity on which pantry and commercial planning layers build.

## MealCandidateAvailability

`MealCandidateAvailability` represents one Family-specific way to obtain or prepare exactly one FoodItem or Recipe.

Supported source kinds are:

- `home` — prepared or obtained at home;
- `pantry` — represented as available from household stock;
- `restaurant` — eat-at-venue source;
- `delivery` — delivery source;
- `store` — retail/shop source.

Each source records:

- Family ownership;
- exactly one FoodItem or Recipe reference;
- source kind and stable `source_key`;
- optional location;
- optional preparation/lead time;
- kitchen requirement;
- explicit operational availability;
- source provenance, external reference and notes.

These rows are current operational state rather than historical recommendation evidence. Catalogue references therefore use `ON DELETE CASCADE`; historical recommendation and Serving records retain their own immutable evidence/provenance.

## Base practical-profile adaptation

`build_persisted_practical_profiles()` loads source rows for one Family and candidate set and produces ordinary `CandidatePracticalProfile` records for the practical recommendation layer.

Deterministic rules:

- Family-specific FoodItem/Recipe objects from another Family are rejected;
- candidates with no persisted source rows remain unknown instead of being excluded;
- modeled candidates with no available source become explicitly unavailable;
- callers can restrict source kinds, for example delivery-only planning;
- preparation time is the minimum known time across usable sources;
- kitchen requirement is true only when all usable sources require a kitchen;
- location is restrictive only when every usable source has an explicit location.

`CandidatePracticalProfile.is_available=False` maps to the normal practical exclusion `candidate_unavailable`.

## Layers built on the source identity

`MealCandidateAvailability` intentionally remains small. More volatile or quantity-aware data is stored in dedicated child/adjacent models.

### Pantry stock

Family pantry inventory is modeled separately with `PantryStockLot`, including quantity, unit, expiry and observation time. Recipe sufficiency and missing shopping quantities are calculated from authoritative pantry lots rather than being encoded directly on a `pantry` source row.

Detailed semantics: `docs/domain/pantry-stock-shopping-requirements.md`, ADR-024.

### Restaurant/delivery/store commercial context

Commercial sources can now have:

- `MealSourceOpeningWindow` weekly local opening windows;
- `MealCommercialOffer` provider-observed price/currency/fee/minimum-order metadata and validity.

Time-aware commercial planning adapts currently usable commercial sources into `CandidatePracticalProfile` while returning active commercial offers separately.

Detailed semantics: `docs/domain/restaurant-delivery-commercial-context.md`, ADR-025.

## Safety boundary

Practical, pantry and commercial context can make a candidate infeasible before ranking, but none of these layers can make a safety-ineligible candidate eligible.

Any candidate that remains practically feasible still passes through adverse-reaction, mandatory NutritionConstraint and deterministic nutrition logic.

Unknown metadata remains distinct from explicit unavailability. Missing pantry/commercial data should not silently become either zero stock or a closed restaurant unless the corresponding domain model has explicit evidence for that conclusion.

## Current limitations

The persisted source stack still intentionally does not provide:

- durable shopping-list/order lifecycle;
- provider API clients, authentication or live sync workers;
- commercial freshness/staleness policy;
- dynamic routing/geographic distance;
- taxes, tips, coupons or basket-level minimum-order satisfaction;
- FX conversion;
- price-aware recommendation ranking;
- live order/cart state.

These capabilities can evolve around the stable source identity without changing FoodItem/Recipe nutrition composition or recommendation safety semantics.

## Related documents

- practical recommendation context: `docs/domain/recommendation-practical-context.md`, ADR-019;
- persisted source identity: ADR-023;
- pantry stock: `docs/domain/pantry-stock-shopping-requirements.md`, ADR-024;
- restaurant/delivery commercial context: `docs/domain/restaurant-delivery-commercial-context.md`, ADR-025.
