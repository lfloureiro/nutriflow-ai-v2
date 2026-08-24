import { useState } from "react";

import DeliveryMenuScreen from "./DeliveryMenuScreen";
import IngredientCatalogue from "./IngredientCatalogue";
import MealDiscoverySettings from "./MealDiscoverySettings";
import PantryScreen from "./PantryScreen";
import RecipeCatalogue from "./RecipeCatalogue";
import RecipePreferences from "./RecipePreferences";
import RestaurantDiscoveryScreen from "./RestaurantDiscoveryScreen";
import ShoppingListScreen from "./ShoppingListScreen";
import { useI18n } from "./i18n";

type HomeBaseView =
  | "recipes"
  | "ingredients"
  | "pantry"
  | "shopping"
  | "preferences"
  | "sources"
  | "restaurants"
  | "delivery";

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
          preferences: "Preferências",
          sources: "Fontes",
          restaurants: "Restaurantes",
          delivery: "Menus entrega",
        }
      : {
          label: "Home management",
          recipes: "Recipes",
          ingredients: "Ingredients",
          pantry: "Pantry",
          shopping: "Shopping",
          preferences: "Preferences",
          sources: "Sources",
          restaurants: "Restaurants",
          delivery: "Delivery menus",
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
        <button
          aria-current={view === "preferences" ? "page" : undefined}
          className={view === "preferences" ? "active" : ""}
          onClick={() => setView("preferences")}
          type="button"
        >
          {copy.preferences}
        </button>
        <button
          aria-current={view === "sources" ? "page" : undefined}
          className={view === "sources" ? "active" : ""}
          onClick={() => setView("sources")}
          type="button"
        >
          {copy.sources}
        </button>
        <button
          aria-current={view === "restaurants" ? "page" : undefined}
          className={view === "restaurants" ? "active" : ""}
          onClick={() => setView("restaurants")}
          type="button"
        >
          {copy.restaurants}
        </button>
        <button
          aria-current={view === "delivery" ? "page" : undefined}
          className={view === "delivery" ? "active" : ""}
          onClick={() => setView("delivery")}
          type="button"
        >
          {copy.delivery}
        </button>
      </nav>
      {view === "recipes" ? <RecipeCatalogue familyId={familyId} /> : null}
      {view === "ingredients" ? <IngredientCatalogue familyId={familyId} /> : null}
      {view === "pantry" ? <PantryScreen familyId={familyId} /> : null}
      {view === "shopping" ? <ShoppingListScreen familyId={familyId} /> : null}
      {view === "preferences" ? <RecipePreferences familyId={familyId} /> : null}
      {view === "sources" ? <MealDiscoverySettings familyId={familyId} /> : null}
      {view === "restaurants" ? <RestaurantDiscoveryScreen familyId={familyId} /> : null}
      {view === "delivery" ? <DeliveryMenuScreen familyId={familyId} /> : null}
    </div>
  );
}
