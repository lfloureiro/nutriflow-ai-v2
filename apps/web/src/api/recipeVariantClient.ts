import { ApiError, buildApiUrl } from "./client";
import type { MealType } from "./mealPlanTypes";

export type VariantOperation={recipe_ingredient_id:string;replacement_food_item_id:string;quantity:string;unit:string;preparation:string};
export type RecipeVariant={id:string;base_recipe_id:string;recipe_id:string;base_name:string;name:string;revision:number;version:number;status:"draft"|"active"|"retired";serving_count:string|null;energy_per_serving:string|null;issues:string[];operations:(VariantOperation&{source_name:string;replacement_name:string})[]};
export type VariantContext={expected_version:number;planning_date:string;meal_type:MealType;participants:{person_id:string;quantity:string}[]};
export type VariantValidation={eligible:boolean;issues:string[];participants:{person_id:string;eligible:boolean;issues:string[];fit:{status:string;explanation:string[]}|null}[]};
async function request<T>(path:string,body?:unknown):Promise<T>{
  const response=await fetch(buildApiUrl(path),{method:body===undefined?"GET":"POST",headers:{"Content-Type":"application/json",Accept:"application/json"},...(body===undefined?{}:{body:JSON.stringify(body)})});
  if(!response.ok){const data=await response.json().catch(()=>({})) as {detail?:unknown};throw new ApiError(typeof data.detail==="string"?data.detail:JSON.stringify(data.detail??`HTTP ${response.status}`),response.status);}
  return response.json() as Promise<T>;
}
const base=(family:string)=>`/api/families/${encodeURIComponent(family)}/recipe-variants`;
export const listRecipeVariants=(family:string,recipe:string)=>request<RecipeVariant[]>(`${base(family)}?base_recipe_id=${encodeURIComponent(recipe)}`);
export const createRecipeVariant=(family:string,data:{base_recipe_id:string;name:string;serving_count:string;operations:VariantOperation[];revises_variant_id?:string})=>request<RecipeVariant>(base(family),data);
export const validateRecipeVariant=(family:string,row:RecipeVariant,context:VariantContext)=>request<VariantValidation>(`${base(family)}/${encodeURIComponent(row.id)}/validate`,context);
export const activateRecipeVariant=(family:string,row:RecipeVariant,context:VariantContext)=>request<RecipeVariant>(`${base(family)}/${encodeURIComponent(row.id)}/activate`,context);
export const retireRecipeVariant=(family:string,row:RecipeVariant)=>request<RecipeVariant>(`${base(family)}/${encodeURIComponent(row.id)}/retire`,{expected_version:row.version});
