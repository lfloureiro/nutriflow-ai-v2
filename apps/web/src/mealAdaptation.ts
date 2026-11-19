import type {ReviewRecipe,Substitution} from "./api/dietaryReviewClient";
import type {VariantOperation} from "./api/recipeVariantClient";
import type {MealPlanEntry} from "./api/mealPlanTypes";
export function suggestedOperation(recipe:ReviewRecipe,ingredientId:string):VariantOperation {
 const ingredient=recipe.ingredients.find(i=>i.id===ingredientId);
 return operationWithSource(recipe,ingredientId,ingredient?.substitutions.find(s=>s.status!=="rejected"));
}
/** Original quantities are editable starting values, not nutritional equivalences. */
export function operationWithSource(recipe:ReviewRecipe,ingredientId:string,proposal?:Substitution):VariantOperation {
 const ingredient=recipe.ingredients.find(i=>i.id===ingredientId);
 const unit=proposal?.replacement_unit??ingredient?.unit??"";
 const quantity=proposal?.replacement_quantity??(unit===ingredient?.unit?ingredient?.quantity??"":"");
 return {recipe_ingredient_id:ingredientId,replacement_food_item_id:proposal?.replacement_food_item_id??"",quantity,unit,preparation:ingredient?.preparation??""};
}

export function positivePortion(value:string):boolean {const text=value.trim().replace(",",".");return !!text && Number.isFinite(Number(text)) && Number(text)>0;}
export function initialPortion(entry:MealPlanEntry|null|undefined,personId:string,portions?:{person_id:string;quantity:string;unit:string}[]):string {
 const saved=entry?.participants.find(p=>p.person_id===personId);
 if(saved)return saved.unit==="serving" ? saved.quantity??"" : "";
 const proposed=portions?.find(p=>p.person_id===personId);
 return proposed?.unit==="serving" ? proposed.quantity : "";
}
export function draftReady(servings:string,operations:VariantOperation[],portions:Record<string,string>,personIds:string[]):boolean {
 return positivePortion(servings)&&operations.length>0&&operations.every(o=>!!o.replacement_food_item_id&&positivePortion(o.quantity)&&["g","ml","un","serving"].includes(o.unit))&&personIds.length>0&&personIds.every(id=>positivePortion(portions[id]??""));
}

export function adaptationIssueLabel(issue:string,pt:boolean):string {
 if(issue.startsWith("base_recipe_changed"))return pt?"A receita base mudou. Prepara uma nova revisão das trocas.":"The base recipe changed. Prepare a new revision.";
 if(issue.startsWith("variant_evidence_changed"))return pt?"Os ingredientes, a receita ou o rótulo mudaram. É necessária nova revisão.":"Ingredient, recipe or label evidence changed. Review again.";
 if(issue.includes("composition_missing"))return pt?"Falta composição nutricional. Completa os ingredientes no catálogo antes de avançar.":"Nutrition composition is missing. Complete the ingredient catalogue before continuing.";
 if(issue.includes("energy_missing"))return pt?"Falta o valor energético para calcular a receita adaptada.":"Energy data is missing for the adapted recipe.";
 if(issue==="ingredient_unavailable")return pt?"Um ingrediente já não está disponível. Escolhe outro no catálogo.":"An ingredient is no longer available. Choose another catalogue item.";
 if(issue.startsWith("active_restriction:"))return (pt?"Restrição ativa para: ":"Active restriction for: ")+issue.slice("active_restriction:".length);
 if(issue.startsWith("plan_fit:"))return pt?"Existem regras por cumprir ou informação por confirmar para esta pessoa.":"This person has unmet rules or evidence requiring review.";
 return issue;
}
export function adaptationFitLabel(status:string,pt:boolean):string {
 const labels:Record<string,[string,string]>={pass:["Regras verificadas","Rules checked"],partial:["Avaliação parcial","Partial assessment"],unknown:["Dados insuficientes para avaliar","Insufficient evidence to assess"],fail:["Regras por cumprir","Unmet rules"],conflict:["Regras em conflito","Conflicting rules"]};
 return labels[status]?.[pt?0:1]??status;
}

export function adaptationMissingData(recipe:ReviewRecipe,servings:string,operations:Record<string,VariantOperation>,portions:Record<string,string>,people:{id:string;first_name:string}[],pt:boolean):string[] {
 const issues:string[]=[];
 if(Object.keys(operations).length&&!positivePortion(servings))issues.push(pt?(recipe.serving_count?"Confirmar quantas doses rende a receita adaptada.":"Rendimento: o número de doses não está registado na receita original."):(recipe.serving_count?"Confirm adapted recipe yield.":"Yield: the original recipe had no recorded serving count."));
 for(const op of Object.values(operations)){
  const label=recipe.ingredients.find(i=>i.id===op.recipe_ingredient_id)?.name??(pt?"Ingrediente":"Ingredient");
  if(!op.replacement_food_item_id)issues.push(`${label}: ${pt?"associar a alternativa a um ingrediente concreto do catálogo.":"identify the replacement catalogue ingredient."}`);
  if(!positivePortion(op.quantity))issues.push(`${label}: ${pt?"definir a quantidade da alternativa na unidade escolhida.":"set replacement quantity in the chosen unit."}`);
  if(!["g","ml","un","serving"].includes(op.unit))issues.push(`${label}: ${pt?"escolher a unidade da alternativa.":"choose the replacement unit."}`);
 }
 for(const person of people)if(!positivePortion(portions[person.id]??""))issues.push(`${person.first_name}: ${pt?"confirmar a porção.":"confirm the portion."}`);
 return issues;
}

export function recipeEditReady(servings:string,operations:VariantOperation[],portions:Record<string,string>,personIds:string[]):boolean {
 return (!servings.trim()||positivePortion(servings))&&operations.length>0&&operations.every(operation=>positivePortion(operation.quantity)&&!!operation.unit.trim())&&personIds.length>0&&personIds.every(id=>positivePortion(portions[id]??""));
}
