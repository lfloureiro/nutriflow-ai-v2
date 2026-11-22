import { describe, expect, it } from "vitest";
import type { ReviewRecipe } from "./api/dietaryReviewClient";
import type { RecipeVariant, VariantOperation } from "./api/recipeVariantClient";
import { equivalentVariant, recipeAdaptationProgress, sameVariantOperations } from "./recipeAdaptationProgress";

const garlic = {recipe_ingredient_id:"g",replacement_food_item_id:"olive-oil",quantity:"12.0000",unit:"ml",preparation:" Infundir e retirar alho "};
const onion = {recipe_ingredient_id:"o",replacement_food_item_id:"chives",quantity:"15",unit:"g",preparation:"Picar"}; 
const variants = [{
  id:"variant-a",status:"draft",serving_count:"4",
  operations:[garlic,onion],
}] as unknown as RecipeVariant[];

const recipe = {
  id:"recipe", name:"Almôndegas",
  ingredients:[
    {id:"g",name:"Alho",food_item_id:"excluded-garlic",substitutions:[{
      status:"proposed",replacement_name:"Azeite infundido",replacement_food_item_id:null,replacement_quantity:null,replacement_unit:null,
    }]},
    {id:"o",name:"Cebola",food_item_id:"excluded-onion",substitutions:[{
      status:"proposed",replacement_name:"Cebolinho",replacement_food_item_id:null,replacement_quantity:null,replacement_unit:null,
    }]},
  ],
} as unknown as ReviewRecipe;

describe("complete family recipe adaptation", () => {
  it("finds an equivalent draft with both swaps irrespective of array order or decimal formatting", () => {
    const reordered = [
      {...onion,quantity:"15.0000",preparation:" picar "},
      {...garlic,quantity:"12",preparation:"Infundir e retirar alho"},
    ] as VariantOperation[];
    expect(sameVariantOperations(reordered,variants[0]!.operations)).toBe(true);
    expect(equivalentVariant(variants,"4.00",reordered)?.id).toBe("variant-a");
    expect(equivalentVariant(variants,"5",reordered)).toBeUndefined();
    expect(equivalentVariant(variants,"4",[{...onion}])).toBeUndefined();
  });

  it("does not mistake a named proposal for a validated ingredient", () => {
    const progress = recipeAdaptationProgress(recipe,["g","o"]);
    expect(progress.status).toBe("needs_product");
    expect(progress.blockedCount).toBe(2);
    expect(progress.issues).toHaveLength(2);
  });

  it("does not label a partial active variant as a complete adaptation", () => {
    const partial = {
      ...recipe, active_variants:[{
        id:"active-1",operations:[{recipe_ingredient_id:"g"}],
      }],
    } as unknown as ReviewRecipe;
    expect(recipeAdaptationProgress(partial,["g","o"]).status).toBe("needs_product");
    const complete = {
      ...recipe, active_variants:[{
        id:"active-2",operations:[{recipe_ingredient_id:"g"},{recipe_ingredient_id:"o"}],
      }],
    } as unknown as ReviewRecipe;
    expect(recipeAdaptationProgress(complete,["g","o"]).status).toBe("active");
  });

  it("keeps missing research and quantity as distinct blockers", () => {
    const missing = {...recipe,ingredients:[
      {...recipe.ingredients[0]!,substitutions:[]},
      {...recipe.ingredients[1]!,substitutions:[{
        id:"proposal",replacement_name:"Cebolinho",status:"proposed",
        replacement_food_item_id:"chives",replacement_quantity:null,replacement_unit:null,notes:"",version:1,
      }]},
    ]} as ReviewRecipe;
    const progress = recipeAdaptationProgress(missing,["g","o"]);
    expect(progress.status).toBe("needs_research");
    expect(progress.issues.some(issue => issue.includes("sem alternativa"))).toBe(true);
    expect(progress.issues.some(issue => issue.includes("quantidade"))).toBe(true);
  });
});
