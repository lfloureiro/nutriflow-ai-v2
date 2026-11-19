import {requestNavigation,type HouseView} from "./navigation";
import { useEffect,useState } from "react";

import DeliveryMenuScreen from "./DeliveryMenuScreen";
import IngredientCatalogue from "./IngredientCatalogue";
import MealDiscoverySettings from "./MealDiscoverySettings";
import PantryScreen from "./PantryScreen";
import RecipeCatalogue from "./RecipeCatalogue";
import RecipeDietaryReview from "./RecipeDietaryReview";
import RecipePreferences from "./RecipePreferences";
import RestaurantDiscoveryScreen from "./RestaurantDiscoveryScreen";
import ShoppingListScreen from "./ShoppingListScreen";
import { useI18n } from "./i18n";

export default function HomeBase({ familyId,initialView="recipes",onViewChange }: { familyId: string;initialView?:HouseView;onViewChange?:(view:HouseView)=>boolean }) {
  const { locale } = useI18n();
  const [view, setLocalView] = useState<HouseView>(initialView);
  useEffect(()=>setLocalView(initialView),[initialView]);
  function setView(next:HouseView){if(onViewChange? !onViewChange(next):!requestNavigation())return;setLocalView(next);}
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
      <nav className="secondary-tabs home-base-tabs nf-house-nav" aria-label={copy.label}>
        {(["recipes", "ingredients", "pantry"] as const).map(item => <button key={item} type="button" aria-current={view === item ? "page" : undefined} className={view === item ? "active" : ""} onClick={() => setView(item)}>{copy[item]}</button>)}
        <details className="nf-house-tools"><summary>{locale === "pt-PT" ? "Mais ferramentas" : "More tools"}</summary><div>
          {(["substitutions", "shopping", "preferences", "sources", "restaurants", "delivery"] as const).map(item => <button key={item} type="button" aria-current={view === item ? "page" : undefined} className={view === item ? "active" : ""} onClick={event => { setView(item); event.currentTarget.closest("details")?.removeAttribute("open"); }}>{item === "substitutions" ? (locale === "pt-PT" ? "Substituições" : "Substitutions") : copy[item]}</button>)}
        </div></details>
      </nav>
      {view === "recipes" ? <RecipeCatalogue familyId={familyId} /> : null}
      {view === "substitutions" ? <RecipeDietaryReview key={familyId} familyId={familyId} /> : null}
      {view === "ingredients" ? <IngredientCatalogue familyId={familyId} /> : null}
      {view === "pantry" ? <PantryScreen familyId={familyId} /> : null}
      {view === "shopping" ? <ShoppingListScreen familyId={familyId} onOpenPantry={()=>setView("pantry")} /> : null}
      {view === "preferences" ? <RecipePreferences familyId={familyId} /> : null}
      {view === "sources" ? <MealDiscoverySettings familyId={familyId} /> : null}
      {view === "restaurants" ? <RestaurantDiscoveryScreen familyId={familyId} /> : null}
      {view === "delivery" ? <DeliveryMenuScreen familyId={familyId} /> : null}
    </div>
  );
}
