# Recipe preferences and recommendation ranking

## Purpose

Recipe preference is human feedback, separate from nutrition suitability and safety eligibility.

The current implementation reuses `FoodPreference` with:

```text
subject_type = recipe
subject_key = <Recipe.recipe_key>
preference_type = rating
intensity = 1..5
```

No new database table or migration is required for this block.

## Product workflow

`Casa -> Preferências` is a focused Family screen:

1. choose a Family Recipe;
2. each Person can rate it from 1 to 5 stars;
3. the screen shows the current Family average and rating count;
4. a Person rating can be replaced or cleared.

The normal recipe editor remains focused on recipe definition and nutrition evidence.

## API

```text
GET    /api/families/{family_id}/recipes/{recipe_id}/preferences
PUT    /api/families/{family_id}/recipes/{recipe_id}/preferences/{person_id}
DELETE /api/families/{family_id}/recipes/{recipe_id}/preferences/{person_id}
```

Family and Person scope are enforced server-side.

The service keeps one current rating per Person/Recipe and removes duplicate rating rows encountered when a rating is updated.

## Recommendation semantics

Hard safety and mandatory nutrition constraints always run first. Ratings never make an excluded candidate eligible.

For one selected Person, a 1..5 rating contributes to the existing personal `preferences` score using a centered scale:

```text
1 star  -> -1.0
2 stars -> -0.5
3 stars ->  0.0
4 stars -> +0.5
5 stars -> +1.0
```

Existing explicit `like` / `dislike` preferences remain supported.

When the recommendation is for exactly one Person, ratings from the other Family members are aggregated per Recipe. Their average contributes a separate secondary `family_preferences` score at half weight:

```text
family score = ((average rating - 3) / 2) * 0.5
```

The selected Person is excluded from this Family average because their rating is already represented by the stronger personal preference component.

When two or more Persons are selected, the shared-Family recommendation engine evaluates every selected Person independently. Their own ratings therefore enter their own personal scores directly. Group ranking then prioritizes the lowest participant score and uses the average participant score as the second ordering key. Unselected Family members do not influence that shared-group score.

This keeps preference ordering explainable:

```text
eligibility first
-> each Person's nutrition fit
-> each Person's preference
-> practical availability/context
-> shared fairness (minimum participant score)
-> shared average score
```

For a one-Person run only, the smaller Family preference signal is added after the selected Person's own preference score.

## Invariants

- rating is always an integer from 1 to 5;
- a Person must belong to the Family owning the Recipe;
- Family average is presentation/ranking evidence, not a safety rule;
- missing ratings are neutral, not zero-star ratings;
- browser code stores ratings but does not calculate recommendation scores;
- selecting multiple Persons does not average away a mandatory exclusion for one member;
- historical recommendation runs preserve their stored score/explanation evidence and are not rewritten when ratings change later.
