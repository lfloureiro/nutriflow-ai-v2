import { useEffect, useMemo, useState } from "react";

import { ApiError, listFamilyPersons, listFamilyRecipes } from "./api/client";
import {
  clearRecipeRating,
  getRecipePreferences,
  setRecipeRating,
} from "./api/recipePreferenceClient";
import type { RecipePreferenceSummary } from "./api/recipePreferenceTypes";
import type { Recipe } from "./api/recipeTypes";
import type { Person } from "./api/types";
import { useI18n } from "./i18n";

const COPY = {
  "pt-PT": {
    eyebrow: "Casa · Preferências",
    title: "Preferências da família",
    help: "Avalia as receitas por pessoa. Estas preferências ajudam a ordenar recomendações, depois das regras obrigatórias de segurança e nutrição.",
    recipe: "Receita",
    chooseRecipe: "Escolher receita",
    familyAverage: "Média da família",
    noRatings: "Ainda sem avaliações",
    ratings: "avaliações",
    loading: "A carregar preferências…",
    noRecipes: "Ainda não existem receitas ativas para avaliar.",
    clear: "Limpar",
    error: "Não foi possível atualizar as preferências",
    star: "estrela",
    stars: "estrelas",
  },
  en: {
    eyebrow: "Home base · Preferences",
    title: "Family preferences",
    help: "Rate recipes per person. These preferences help order recommendations after mandatory safety and nutrition rules.",
    recipe: "Recipe",
    chooseRecipe: "Choose recipe",
    familyAverage: "Family average",
    noRatings: "No ratings yet",
    ratings: "ratings",
    loading: "Loading preferences…",
    noRecipes: "There are no active recipes to rate yet.",
    clear: "Clear",
    error: "Preferences could not be updated",
    star: "star",
    stars: "stars",
  },
} as const;

function errorText(error: unknown): string {
  if (error instanceof ApiError) return `${error.message} (HTTP ${error.status})`;
  return error instanceof Error ? error.message : String(error);
}

function displayName(person: Person): string {
  return [person.first_name, person.last_name].filter(Boolean).join(" ");
}

function averageText(summary: RecipePreferenceSummary | null, locale: string): string {
  if (!summary || summary.average_rating === null) return "—";
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(
    Number(summary.average_rating),
  );
}

export default function RecipePreferences({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [recipeId, setRecipeId] = useState("");
  const [summary, setSummary] = useState<RecipePreferenceSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingPersonId, setSavingPersonId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void Promise.all([listFamilyRecipes(familyId), listFamilyPersons(familyId)])
      .then(([recipeResult, peopleResult]) => {
        if (cancelled) return;
        setRecipes(recipeResult);
        setPeople(peopleResult);
        setRecipeId((current) =>
          recipeResult.some((recipe) => recipe.id === current)
            ? current
            : (recipeResult[0]?.id ?? ""),
        );
      })
      .catch((caught: unknown) => {
        if (!cancelled) setError(errorText(caught));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [familyId]);

  useEffect(() => {
    if (!recipeId) {
      setSummary(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    void getRecipePreferences(familyId, recipeId)
      .then((result) => {
        if (!cancelled) setSummary(result);
      })
      .catch((caught: unknown) => {
        if (!cancelled) setError(errorText(caught));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [familyId, recipeId]);

  const ratingByPerson = useMemo(
    () => new Map(summary?.ratings.map((rating) => [rating.person_id, rating.rating]) ?? []),
    [summary],
  );

  async function rate(personId: string, rating: number) {
    if (!recipeId) return;
    setSavingPersonId(personId);
    setError(null);
    try {
      setSummary(await setRecipeRating(familyId, recipeId, personId, { rating }));
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setSavingPersonId(null);
    }
  }

  async function clear(personId: string) {
    if (!recipeId) return;
    setSavingPersonId(personId);
    setError(null);
    try {
      setSummary(await clearRecipeRating(familyId, recipeId, personId));
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setSavingPersonId(null);
    }
  }

  return (
    <div className="recipe-preferences-screen">
      <header className="screen-header compact-screen-header">
        <div>
          <span className="eyebrow">{copy.eyebrow}</span>
          <h1>{copy.title}</h1>
          <p>{copy.help}</p>
        </div>
      </header>

      {error ? (
        <div className="error-banner" role="alert">
          <strong>{copy.error}</strong>
          <span>{error}</span>
        </div>
      ) : null}

      {recipes.length === 0 && !loading ? (
        <div className="ingredient-empty">{copy.noRecipes}</div>
      ) : (
        <>
          <div className="recipe-preference-toolbar">
            <label className="field">
              <span>{copy.recipe}</span>
              <select value={recipeId} onChange={(event) => setRecipeId(event.target.value)}>
                <option value="">{copy.chooseRecipe}</option>
                {recipes.map((recipe) => (
                  <option key={recipe.id} value={recipe.id}>{recipe.name}</option>
                ))}
              </select>
            </label>
            <div className="recipe-preference-average">
              <span>{copy.familyAverage}</span>
              <strong>{averageText(summary, locale)} / 5</strong>
              <small>
                {summary && summary.rating_count > 0
                  ? `${summary.rating_count} ${copy.ratings}`
                  : copy.noRatings}
              </small>
            </div>
          </div>

          {loading ? <div className="shell-loading" role="status">{copy.loading}</div> : null}

          {!loading && recipeId ? (
            <div className="recipe-preference-people">
              {people.map((person) => {
                const current = ratingByPerson.get(person.id) ?? null;
                const saving = savingPersonId === person.id;
                return (
                  <div className="recipe-preference-person" key={person.id}>
                    <strong>{displayName(person)}</strong>
                    <div className="recipe-stars" aria-label={displayName(person)}>
                      {[1, 2, 3, 4, 5].map((rating) => (
                        <button
                          aria-label={`${rating} ${rating === 1 ? copy.star : copy.stars}`}
                          className={current !== null && rating <= current ? "selected" : ""}
                          disabled={saving}
                          key={rating}
                          onClick={() => void rate(person.id, rating)}
                          type="button"
                        >
                          ★
                        </button>
                      ))}
                    </div>
                    <span className="recipe-person-rating">{current === null ? "—" : `${current}/5`}</span>
                    <button
                      className="button ghost"
                      disabled={saving || current === null}
                      onClick={() => void clear(person.id)}
                      type="button"
                    >
                      {copy.clear}
                    </button>
                  </div>
                );
              })}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
