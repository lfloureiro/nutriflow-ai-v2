import type {Recipe,RecipeMealType} from "./api/recipeTypes";
export type RecipeBrowse={query:string;includeInactive:boolean;nutrition:"all"|"ingredient_calculated"|"incomplete"|"synthetic_development";meal:"all"|RecipeMealType;origin:"all"|"shared"|"family"|"adapted";sort:"name"|"updated"|"ingredients"};
export const defaultRecipeBrowse:RecipeBrowse={query:"",includeInactive:false,nutrition:"all",meal:"all",origin:"all",sort:"name"};
export const searchText=(value:string)=>value.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase().trim();
export const isAdaptedRecipe=(recipe:Recipe)=>["family_adaptation","family_variant"].includes(recipe.source);
export function browseRecipes(recipes:Recipe[],browse:RecipeBrowse,locale:string):Recipe[]{
 return recipes.filter(recipe=>(browse.meal==="all"||recipe.suitable_meal_types.includes(browse.meal))&&(browse.origin==="all"||(browse.origin==="adapted"?isAdaptedRecipe(recipe):browse.origin==="shared"?recipe.scope==="shared":recipe.scope==="family"&&!isAdaptedRecipe(recipe)))).slice().sort((a,b)=>browse.sort==="updated"?b.updated_at.localeCompare(a.updated_at)||a.name.localeCompare(b.name,locale):browse.sort==="ingredients"?a.ingredients.length-b.ingredients.length||a.name.localeCompare(b.name,locale):a.name.localeCompare(b.name,locale));
}
export function readRecipeBrowse(familyId:string):RecipeBrowse{
 try{const raw=JSON.parse(sessionStorage.getItem(`nf-recipe-browse:${familyId}`)??"{}");return {...defaultRecipeBrowse,query:typeof raw.query==="string"?raw.query.slice(0,200):"",includeInactive:raw.includeInactive===true,nutrition:["all","ingredient_calculated","incomplete","synthetic_development"].includes(raw.nutrition)?raw.nutrition:"all",meal:["all","breakfast","lunch","snack","dinner"].includes(raw.meal)?raw.meal:"all",origin:["all","shared","family","adapted"].includes(raw.origin)?raw.origin:"all",sort:["name","updated","ingredients"].includes(raw.sort)?raw.sort:"name"};}catch{return {...defaultRecipeBrowse};}
}
export function storeRecipeBrowse(familyId:string,value:RecipeBrowse){try{sessionStorage.setItem(`nf-recipe-browse:${familyId}`,JSON.stringify(value));}catch{/* Browsing remains functional with unavailable storage. */}}
