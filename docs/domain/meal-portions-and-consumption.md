# Meal portions and consumption

## Purpose

NutriFlow separates three concepts that must not be conflated:

1. the Person's daily energy target;
2. the amount recommended for one meal;
3. the amount actually eaten.

Recommendation uses the first two. Daily nutrition state ultimately follows the third.

## Meal energy allocation v1

Version: `meal-energy-allocation-v1`.

The first deterministic allocation policy uses these shares of the Person's daily energy target:

| Meal | Share |
| --- | ---: |
| Breakfast | 25% |
| Lunch | 35% |
| Snack | 10% |
| Dinner | 30% |

The daily target is reconstructed from the authoritative daily state:

`consumed + planned + assumed + remaining`.

The meal target is the corresponding share of the daily target, bounded by the energy still available for the day. This prevents a late meal from being allocated more energy than remains in the daily budget.

These shares are an explicit v1 heuristic. They are not a medical claim and can later become Person-specific or adaptive without rewriting historical recommendation runs.

## Automatic portion sizing v1

Version: `portion-sizing-v1`.

Automatic sizing is opt-in at API level through `auto_size_portions`. Current NutriFlow Web requests enable it; older clients that omit the field retain the previous fixed-portion semantics.

For each candidate and Person:

1. calculate the meal energy target midpoint;
2. divide it by the candidate's energy at its catalogue portion;
3. clamp the factor to 0.50–2.00;
4. round to the nearest 0.25 portion;
5. rebuild candidate nutrition at the adjusted quantity;
6. run safety, nutrient and ranking logic on that adjusted nutrition.

Examples:

- a 500 kcal standard portion against a 630–700 kcal lunch target becomes 1.25 portions;
- the same dish can be 1.25 portions for one Person and 1.50 portions for another;
- extreme suggestions are bounded rather than producing impractical 0.13 or 4.7 portion values.

Shared Family recommendations therefore keep one MealEvent but can materialize a different Serving quantity for each participant.

The individual practical recommendation run stores the allocation policy and candidate portion factors in run context. Engine versions include `+portion-sizing-v1` when sizing is enabled.

## Commercial offers

The recommended quantity describes how much of the candidate the Person should eat. A commercial offer still represents the provider's listed item price. In v1 this does **not** yet multiply the commercial price when a recommended amount exceeds one provider item.

A later commercial-order layer must translate recommended edible portion into whole order items, leftovers and true order cost. Until then the UI/provider price must not imply that fractional or multiple provider items have already been priced.

## Consumption recording

A planned Serving can be recorded as:

- `consumed`: the full served/planned quantity was eaten unless an explicit quantity is supplied by a lower-level integration;
- `partial`: requires the actual quantity eaten;
- `skipped`: explicitly records that the Person did not eat that Serving.

For catalogue-backed Servings, nutrition is recalculated from the immutable composition snapshot at the actual consumed quantity. If a legacy Serving has planned nutrition but no catalogue composition, the consumed nutrition is scaled proportionally from planned quantity as an explicit fallback.

After consumption is recorded, the Person's DailyNutritionState is recalculated immediately. Real user activity forces replacement of a synthetic development baseline so demo behaviour follows the same accounting path as production after the first real action.

## Breakfast semantics

After the configured breakfast cutoff, an undeclared breakfast can contribute `energy_assumed_kcal` through the Person's standard-breakfast estimate.

An explicitly skipped breakfast is different from an undeclared breakfast:

- undeclared -> standard breakfast energy may be assumed;
- planned/consumed breakfast -> real planned/consumed energy is used;
- explicitly skipped breakfast -> known 0 kcal; no standard breakfast assumption is applied later that day.

This allows NutriFlow to distinguish missing information from a deliberate decision not to eat.

## State progression

Consumption updates Serving and MealParticipant status. MealEvent status is derived from its participants:

- some participants have eaten -> `served`;
- all participants are realized (`consumed`, `partial` or `skipped`) -> `completed`;
- all skipped can complete without pretending that food was served.

Cancelled or replaced MealEvents cannot record consumption.

## Next evolution

The deterministic v1 allocation intentionally leaves room for:

- redistribution of unused breakfast/snack calories across remaining meal slots;
- Person-specific meal-share preferences;
- activity-aware intraday adjustment;
- commercial whole-item ordering and leftover accounting;
- outcome feedback such as satiety and portion-too-small/too-large;
- learning a bounded portion preference from actual consumption history.

Any future learned signal remains subordinate to mandatory safety and nutrition constraints.
