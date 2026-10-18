import type {ReviewRecipe} from "./api/dietaryReviewClient";
import type {MealPlanEntry} from "./api/mealPlanTypes";
import {savedMealChanges} from "./mealAlternatives";
import {useI18n} from "./i18n";
export default function SavedMealChanges({entry,recipes}:{entry:Pick<MealPlanEntry,"recipe_id"|"variant_changes"|"transformations">;recipes:ReviewRecipe[]}){
  const {locale}=useI18n();const info=savedMealChanges(entry,recipes);
  return <span className="saved-meal-changes">{info.changes.map(change=><span key={change} className={`saved-meal-change ${info.kind}`}><b>{info.kind==="applied"?(locale==="pt-PT"?"Aplicado: ":"Applied: "):(locale==="pt-PT"?"Por aplicar: ":"Not applied: ")}</b>{change}</span>)}</span>;
}
