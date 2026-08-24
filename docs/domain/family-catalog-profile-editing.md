# Family catalogue and profile editing

## Scope

This block makes Family configuration, Person energy profiles and the shared food catalogue operational from the web UI without weakening the existing provenance rules.

No database migration is required. The block reuses the existing versioned Person, Food and Recipe models.

## Family editing

`Mais -> Dados da família` edits the server-authoritative Family record:

- Family name;
- IANA timezone;
- delivery address;
- restaurant area;
- selected meal-discovery sources.

IANA timezone names are validated by the API. Invalid names are rejected instead of being persisted and failing later during planning/date calculations.

The screen also shows meal-discovery capability state. Selection and capability are different concepts:

- **selected** means the Family wants that source;
- **ready/live** means the current installation can actually query it;
- **needs configuration** means required Family configuration is missing;
- **integration required/disabled** means the source cannot currently be used live.

## Person editing

`Pessoas -> Pessoa -> Perfil -> Editar perfil` edits identity and energy-planning inputs.

Identity fields:

- first name;
- last name;
- birth date;
- IANA timezone.

Energy fields:

- sex used by the energy formula;
- height;
- weight;
- habitual activity level;
- maintain/lose/gain goal;
- target weekly rate when relevant;
- standard-breakfast energy assumption.

### Versioning rules

Changing identity-only fields must not create redundant energy history.

When an energy dependency changes, a new active energy target is calculated and the prior target/goal is superseded. Height and weight measurements are appended only when their values actually change. Historical values are never rewritten.

The Family dashboard is refreshed after a Person edit so names/timezones do not remain stale in list views.

## Ingredient catalogue visibility

A Family can see two scopes in `Casa -> Ingredientes`:

1. Family ingredients (`family_id == Family.id`), editable by that Family;
2. shared ingredients (`family_id IS NULL`), visible and read-only.

This is required for legacy-v1 recipes: an ingredient referenced by a visible shared Recipe must not disappear from the Ingredient catalogue merely because it is shared.

Each visible Ingredient also reports the number of active Recipes visible to that Family that use it. Private Recipes from other Families never contribute to this count.

The UI exposes lightweight nutrition-quality filters:

- with energy;
- composition present but energy missing;
- composition missing.

## Recipe nutrition evidence

A numeric calorie value alone is not sufficient to call Recipe nutrition trustworthy. Every Recipe composition returned by the catalogue API has an explicit evidence class:

```text
ingredient_calculated
synthetic_development
imported
unknown
```

### `ingredient_calculated`

The existing deterministic Recipe calculator attempted to derive the Recipe composition from the latest Ingredient compositions.

Energy is usable only when every Ingredient has energy evidence and its Recipe quantity can be safely converted to the composition reference unit.

Missing evidence is never silently converted to zero.

### `synthetic_development`

This is development-only data. In particular, legacy-v1 demo Recipe structure is real imported structure, but the old development fixture contains synthetic Recipe-level nutrition estimates.

Those values remain useful for exercising recommendation/planning flows, but the UI must label them as **development estimates** and must never present them as equivalent to nutrition calculated from Ingredient evidence.

The synthetic estimate can coexist with a list of Ingredients that still lack nutrition; this is intentional and makes the gap explicit.

### `imported`

A non-null composition not produced by the current deterministic Ingredient calculator and not marked as a synthetic development fixture is treated as imported evidence. Provenance fields remain authoritative.

### `unknown`

Used when the system cannot classify the evidence safely. Unknown provenance must remain visible as unknown rather than being upgraded to trusted evidence by inference.

## Recipe catalogue UX

`Casa -> Receitas` exposes nutrition-quality filters:

- all;
- calculated from Ingredients;
- incomplete;
- development estimates.

Recipe detail identifies the exact Ingredients blocking deterministic energy calculation:

- no composition;
- composition exists but energy is missing;
- unit conversion issue.

When a Family-owned Ingredient composition changes, Family-owned Recipes using it are recalculated through the existing deterministic calculator.

## Restaurant discovery UX

Restaurant discovery remains external and may fail even when local configuration is valid.

The UI therefore separates:

- installation/configuration capability;
- a live provider request.

A provider outage is shown as a temporary external-service failure rather than exposing only a raw `HTTP 503` message. Disabled discovery prevents submission. Missing default Family area is explained, while still allowing an explicit area in the search screen.

## Smoke-test checklist

After API CI and Web CI are green on the exact final head:

1. edit Family name/timezone/restaurant area and confirm the shell refreshes;
2. edit a Person name only and confirm no visible energy regression;
3. edit Person weight/activity and confirm target/profile refresh;
4. open Ingredients and confirm legacy/shared Ingredients are visible and read-only;
5. verify Ingredient nutrition filters and Recipe usage counts;
6. open a legacy-v1 Recipe and confirm synthetic nutrition is clearly labelled as a development estimate;
7. open an incomplete Recipe and confirm exact blocking Ingredients are listed;
8. create/edit a Family Ingredient with energy, use it in a Family Recipe and confirm Recipe calories are calculated automatically;
9. verify Recipe nutrition-quality filters;
10. open Restaurants and verify capability messaging and friendly provider-failure handling.

Do not use `docker compose down -v` for this smoke test. The development PostgreSQL volume may contain local data that must be preserved.
