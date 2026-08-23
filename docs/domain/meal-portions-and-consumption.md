# Meal portions and consumption

## Purpose

NutriFlow separates three concepts that must not be conflated:

1. the Person's daily energy target;
2. the amount recommended for one meal;
3. the amount actually eaten.

Recommendation uses the first two. Daily nutrition state ultimately follows the third.

## Meal energy allocation v2

Version: `meal-energy-allocation-v2`.

The deterministic policy retains these base shares:

| Meal | Base share |
| --- | ---: |
| Breakfast | 25% |
| Lunch | 35% |
| Snack | 10% |
| Dinner | 30% |

They are weights, not rigid calorie reservations. NutriFlow redistributes the energy that is still available across the current and remaining meal slots.

For the current meal:

`meal target = remaining daily energy × current meal weight / sum(current + later meal weights)`

This means earlier outcomes automatically affect later recommendations without rewriting the Person's daily target.

Examples:

- after 350 kcal have already been consumed or explicitly assumed, with 1450–1650 kcal remaining, lunch receives about 676.67–770 kcal because lunch is 35/75 of the remaining meal weights;
- if breakfast is explicitly skipped and 1800–2000 kcal remain, lunch receives about 840–933.33 kcal;
- at dinner there are no later meal slots, so dinner uses the energy still available for the day.

The daily target is reconstructed from the authoritative daily state:

`consumed + planned + assumed + remaining`.

The base shares are an explicit heuristic. They are not a medical claim and can later become Person-specific or activity-aware without rewriting historical recommendation runs.

## Automatic portion sizing v1

Version: `portion-sizing-v1`.

Automatic sizing is opt-in at API level through `auto_size_portions`. NutriFlow Web enables it on its recommendation calls; external/older clients that omit the field retain the previous fixed-portion semantics.

For each candidate and Person:

1. calculate the dynamically redistributed meal energy target midpoint;
2. divide it by the candidate's energy at its catalogue portion;
3. clamp the factor to 0.50–2.00;
4. round to the nearest 0.25 portion;
5. rebuild candidate nutrition at the adjusted quantity;
6. run safety, nutrient and ranking logic on that adjusted nutrition.

The energy score uses the meal-specific energy target after sizing, while the daily remaining maximum remains a hard whole-day cap. Therefore a correctly sized lunch is not penalized for being much smaller than all calories remaining until the end of the day.

The same dish can have different quantities for different people. Extreme suggestions are bounded rather than producing impractical values such as 0.13 or 4.7 portions.

Shared Family recommendations therefore keep one MealEvent but can materialize a different Serving quantity for each participant.

The individual practical recommendation run stores the allocation policy, meal targets and candidate portion factors in run context. Engine versions include `+portion-sizing-v1` when sizing is enabled.

## Commercial offers

The recommended quantity describes how much of the candidate the Person should eat. A commercial offer still represents the provider's listed item price. In this version it does **not** yet multiply the commercial price when a recommended amount exceeds one provider item.

A later commercial-order layer must translate recommended edible portion into whole order items, leftovers and true order cost. Until then the UI/provider price must not imply that fractional or multiple provider items have already been priced.

## Consumption recording

A planned Serving can be recorded as:

- `consumed`: the full served/planned quantity was eaten unless an explicit quantity is supplied by a lower-level integration;
- `partial`: requires the actual quantity eaten;
- `skipped`: explicitly records that the Person did not eat that Serving.

For catalogue-backed Servings, nutrition is recalculated from the immutable composition snapshot at the actual consumed quantity. If a legacy Serving has planned nutrition but no catalogue composition, the consumed nutrition is scaled proportionally from planned quantity as an explicit fallback.

After consumption is recorded, the Person's DailyNutritionState is recalculated immediately. Real user activity can replace a synthetic development baseline so demo behaviour follows the production accounting path once actual meal data exists.

## Breakfast semantics

After the configured breakfast cutoff, an undeclared breakfast can contribute `energy_assumed_kcal` through the Person's standard-breakfast estimate.

An explicitly skipped breakfast is different from an undeclared breakfast:

- undeclared -> standard breakfast energy may be assumed;
- planned/consumed breakfast -> real planned/consumed energy is used;
- explicitly skipped breakfast -> known 0 kcal; no standard breakfast assumption is applied later that day.

Because meal allocation v2 redistributes remaining energy, a skipped or unusually small breakfast can increase the sensible target for lunch and later meals. An unusually large earlier meal decreases later targets.

## State progression

Consumption updates Serving and MealParticipant status. MealEvent status is derived from its participants:

- some participants have eaten -> `served`;
- all participants are realized (`consumed`, `partial` or `skipped`) -> `completed`;
- if everybody skipped, the event can be completed with `served_at = null`, avoiding a false claim that food was served.

Cancelled or replaced MealEvents cannot record consumption.

## Next evolution

The deterministic policies intentionally leave room for:

- Person-specific meal-share preferences;
- activity-aware intraday adjustment;
- commercial whole-item ordering and leftover accounting;
- outcome feedback such as satiety and portion-too-small/too-large;
- learning a bounded portion preference from actual consumption history.

Any future learned signal remains subordinate to mandatory safety and nutrition constraints.
