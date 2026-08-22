# ADR-026: Mandatory nutrient maxima require candidate nutrient data

## Status

Accepted

## Context

NutriFlow evaluates mandatory nutrient maximum constraints before recommendation ranking. A candidate can only be considered safe for a mandatory maximum when the recommendation engine has a concrete value for the constrained nutrient in the selected versioned composition snapshot.

Previously, a missing candidate nutrient component was treated like no contribution and therefore allowed the candidate to remain eligible. That conflated unknown data with a measured value of zero and could under-estimate exposure to a nutrient that has a non-negotiable maximum.

## Decision

When an active mandatory nutrient maximum (`max`, `lte` or `<=`) applies to a candidate, the candidate must contain an explicit value for the constrained nutrient.

If the nutrient component is absent from the candidate nutrition snapshot, the candidate is excluded with:

```text
mandatory_nutrient_data_missing:<nutrient_key>
```

An explicit nutrient value of zero is valid data and is evaluated normally.

The exclusion is candidate-scoped. Other candidates with complete nutrient data continue through mandatory checks and deterministic ranking.

Unsupported mandatory constraint semantics and unsafe required unit conversions continue to stop recommendation with `UnsupportedMandatoryConstraintError`.

## Consequences

Positive consequences:

- unknown nutrient values can no longer silently pass a mandatory maximum;
- missing data is distinguished from a real zero value;
- the engine remains fail-closed without unnecessarily aborting candidates that have sufficient data;
- exclusion evidence remains explicit and can be persisted in recommendation history.

Trade-offs:

- catalogue candidates with incomplete composition may become unavailable when a mandatory nutrient limit applies;
- catalogue/provider enrichment must supply the constrained nutrient before those candidates can be recommended under that rule;
- this decision does not by itself define how a missing historical DailyNutritionState nutrient total should be handled; that requires an explicit policy if the state cannot represent the constrained nutrient.

## Rejected alternatives

### Treat a missing candidate nutrient as zero

Rejected because absence of data is not evidence of zero contribution.

### Abort the entire recommendation run for one incomplete candidate

Rejected because the unknown data is candidate-specific. Other candidates with complete evidence can still be evaluated safely.

### Let ranking penalize incomplete candidates instead of excluding them

Rejected because mandatory limits are eligibility rules, not ranking preferences.
