import { useState } from "react";

import IngredientCatalogue from "./IngredientCatalogue";
import RecipeCatalogue from "./RecipeCatalogue";
import { useI18n } from "./i18n";

type HomeBaseView = "recipes" | "ingredients";

export default function HomeBase({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const [view, setView] = useState<HomeBaseView>("recipes");
  const copy =
    locale === "pt-PT"
      ? { label: "Gestão da casa", recipes: "Receitas", ingredients: "Ingredientes" }
      : { label: "Home management", recipes: "Recipes", ingredients: "Ingredients" };

  return (
    <div className="home-base">
      <nav className="secondary-tabs home-base-tabs" aria-label={copy.label}>
        <button
          aria-current={view === "recipes" ? "page" : undefined}
          className={view === "recipes" ? "active" : ""}
          onClick={() => setView("recipes")}
          type="button"
        >
          {copy.recipes}
        </button>
        <button
          aria-current={view === "ingredients" ? "page" : undefined}
          className={view === "ingredients" ? "active" : ""}
          onClick={() => setView("ingredients")}
          type="button"
        >
          {copy.ingredients}
        </button>
      </nav>
      {view === "recipes" ? (
        <RecipeCatalogue familyId={familyId} />
      ) : (
        <IngredientCatalogue familyId={familyId} />
      )}
    </div>
  );
}
