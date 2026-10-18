import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import RecipeAdaptationCards from "./RecipeAdaptationCards";
import type { ReviewRecipe } from "./api/dietaryReviewClient";

vi.mock("./i18n",()=>({useI18n:()=>({locale:"pt-PT"})}));

describe("visible base recipe adaptations",()=>{
  it("shows the active complete variant even when no standalone proposal exists",()=>{
    const recipes=[{id:"r",name:"Massa",ingredients:[{id:"i",food_item_id:"f",name:"Trigo",substitutions:[]}],active_variants:[{id:"v",recipe_id:"vr",name:"Arroz familiar",operations:[{recipe_ingredient_id:"i",replacement_name:"Massa de arroz",quantity:"120",unit:"g",preparation:"Cozinhar"}]}]}] as unknown as ReviewRecipe[];
    const html=renderToStaticMarkup(<RecipeAdaptationCards recipes={recipes} excluded={["f"]} products={[]} people={[]} restrictions={{excluded_food_item_ids:["f"],warnings:[],sources:[]}}/>);
    expect(html).toContain("Trigo → Massa de arroz");
    expect(html).toContain("Arroz familiar");
    expect(html).toContain("120");
    expect(html).not.toContain("alternativa por definir");
    expect(html).not.toContain("Ainda não existe uma alternativa");
  });
  it("keeps the base name and shows each substitution, reason and unresolved dose immediately",()=>{
    const recipes=[{id:"r",name:"Esparguete da família",ingredients:[
      {id:"i",food_item_id:"f",name:"Esparguete de trigo",substitutions:[
        {id:"s",replacement_name:"Esparguete de arroz",status:"proposed",replacement_quantity:null,notes:"Rever dose."},
        {id:"x",replacement_name:"Alternativa recusada",status:"rejected",notes:""},
      ]},
      {id:"i2",food_item_id:"f2",name:"Cebola",substitutions:[]},
    ]}] as unknown as ReviewRecipe[];
    const html=renderToStaticMarkup(<RecipeAdaptationCards recipes={recipes} excluded={["f","f2"]} products={[]} people={[{id:"p",first_name:"Patrícia"}]} restrictions={{excluded_food_item_ids:["f"],warnings:[],sources:[{person_id:"p",source_id:"c",source_kind:"condition",label:"SIBO",food_item_ids:["f"],dates:["2026-10-19"],meal_types:["dinner"]}]}}/>);
    expect(html).toContain("Esparguete da família");
    expect(html).toContain("Esparguete de trigo → Esparguete de arroz");
    expect(html).toContain("Patrícia · SIBO");
    expect(html).toContain("Quantidade por definir");
    expect(html).toContain("Cebola → alternativa por definir");
    expect(html).not.toContain("Alternativa recusada");
    expect(html).not.toContain("<details><summary>Esparguete");
  });
});
