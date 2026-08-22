import { useState } from "react";

import IngredientCatalogue from "./IngredientCatalogue";
import PantryScreen from "./PantryScreen";
import RecipeCatalogue from "./RecipeCatalogue";
import ShoppingListScreen from "./ShoppingListScreen";
import { useI18n } from "./i18n";

type HomeBaseView = "recipes" | "ingredients" | "pantry" | "shopping";

export default function HomeBase({ familyId }: { familyId: string }) {
  const { locale } = useI18n();
  const [view, setView] = useState<HomeBaseView>("recipes");
  const copy =
    locale === "pt-PT"
      ? {
          label: "Gestão da casa",
          recipes: "Receitas",
          ingredients: "Ingredientes",
          pantry: "Despensa",
          shopping: "Compras",
        }
      : {
          label: "Home management",
          recipes: "Recipes",
          ingredients: "Ingredients",
          pantry: "Pantry",
          shopping: "Shopping",
        };

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
        <button
          aria-current={view === "pantry" ? "page" : undefined}
          className={view === "pantry" ? "active" : ""}
          onClick={() => setView("pantry")}
          type="button"
        >
          {copy.pantry}
        </button>
        <button
          aria-current={view === "shopping" ? "page" : undefined}
          className={view === "shopping" ? "active" : ""}
          onClick={() => setView("shopping")}
          type="button"
        >
          {copy.shopping}
        </button>
      </nav>
      {view === "recipes" ? <RecipeCatalogue familyId={familyId} /> : null}
      {view === "ingredients" ? <IngredientCatalogue familyId={familyId} /> : null}
      {view === "pantry" ? <PantryScreen familyId={familyId} /> : null}
      {view === "shopping" ? <ShoppingListScreen familyId={familyId} /> : null}
    </div>
  );
}
