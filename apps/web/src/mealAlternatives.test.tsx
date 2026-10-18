import {describe,it,expect,vi} from "vitest";
import {renderToStaticMarkup} from "react-dom/server";
import {calendarMonday,calendarDateOffset,recipeProposedChanges,savedMealChanges,foodAlternativeNames} from "./mealAlternatives";
import type {ReviewRecipe} from "./api/dietaryReviewClient";
import IngredientAlternativeLine from "./IngredientAlternativeLine";
import SavedMealChanges from "./SavedMealChanges";
vi.mock("./i18n",()=>({useI18n:()=>({locale:"pt-PT"})}));
const recipes=[{id:"r",ingredients:[{name:"Natas",food_item_id:"f",substitutions:[{status:"proposed",replacement_name:"Natas sem lactose"},{status:"rejected",replacement_name:"Recusada"}]}]},{id:"other",ingredients:[{name:"Outro",food_item_id:"other",substitutions:[{status:"proposed",replacement_name:"Outra troca"}]}]}] as unknown as ReviewRecipe[];
describe("saved weeks and inline alternatives",()=>{
  it("keeps substitutions on the selected recipe and omits rejected proposals",()=>{
    expect(recipeProposedChanges(recipes,"r")).toEqual(["Natas → Natas sem lactose"]);
    expect(recipeProposedChanges(recipes,"missing")).toEqual([]);
    expect(foodAlternativeNames(recipes,"f")).toEqual(["Natas sem lactose"]);
  });
  it("distinguishes a pending swap from the actual immutable variant",()=>{
    const entry={recipe_id:"r",transformations:[],variant_changes:[]};
    expect(savedMealChanges(entry,recipes)).toEqual({kind:"proposed",changes:["Natas → Natas sem lactose"]});
    expect(savedMealChanges({...entry,variant_changes:["Natas → Produto confirmado 100 g"]},recipes)).toEqual({kind:"applied",changes:["Natas → Produto confirmado 100 g"]});
    const html=renderToStaticMarkup(<SavedMealChanges entry={entry} recipes={recipes}/>);
    expect(html).toContain("Por aplicar:");expect(html).toContain("Natas sem lactose");expect(html).not.toContain("Outra troca");
  });
  it("puts the ingredient and alternative in one line without changing quantities",()=>{
    const html=renderToStaticMarkup(<IngredientAlternativeLine name="Natas" quantity="2 emb" alternatives={["Natas sem lactose"]}/>);
    expect(html).toContain("Natas · 2 emb");expect(html).toContain("→");expect(html).toContain("Natas sem lactose");expect(html).toContain("por aplicar");
    expect(html).not.toContain("<details");
  });
  it("browses calendar weeks correctly across Sunday, Monday and year boundaries",()=>{
    expect(calendarMonday("2026-10-18")).toBe("2026-10-12");
    expect(calendarMonday("2026-10-19")).toBe("2026-10-19");
    expect(calendarDateOffset("2026-12-28",7)).toBe("2027-01-04");
  });
});
