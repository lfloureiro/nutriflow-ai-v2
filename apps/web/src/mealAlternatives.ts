import type {ReviewRecipe} from "./api/dietaryReviewClient";
import type {MealPlanEntry} from "./api/mealPlanTypes";

export function calendarDateOffset(value:string,days:number){const date=new Date(`${value}T12:00:00Z`);date.setUTCDate(date.getUTCDate()+days);return date.toISOString().slice(0,10);}
export function calendarMonday(value:string){const date=new Date(`${value}T12:00:00Z`);return calendarDateOffset(value,-(date.getUTCDay()+6)%7);}
export function recipeProposedChanges(recipes:ReviewRecipe[],recipeId:string|null|undefined):string[]{
  const recipe=recipes.find(r=>r.id===recipeId);
  return recipe?.ingredients.flatMap(i=>{
    const names=[...new Set(i.substitutions.filter(s=>s.status!=="rejected").map(s=>s.replacement_name))];
    return names.length?[`${i.name} → ${names.join(" / ")}`]:[];
  })??[];
}
export function savedMealChanges(entry:Pick<MealPlanEntry,"recipe_id"|"variant_changes"|"transformations">,recipes:ReviewRecipe[]){
  const actual=entry.variant_changes?.length ? entry.variant_changes : entry.transformations.map(t=>`${t.source_food_name} → ${t.replacement_food_name}`);
  return actual.length?{kind:"applied" as const,changes:actual}:{kind:"proposed" as const,changes:recipeProposedChanges(recipes,entry.recipe_id)};
}
export function foodAlternativeNames(recipes:ReviewRecipe[],foodId:string|null|undefined){
  return [...new Set(recipes.flatMap(r=>r.ingredients.filter(i=>i.food_item_id===foodId).flatMap(i=>i.substitutions.filter(s=>s.status!=="rejected").map(s=>s.replacement_name))))];
}
