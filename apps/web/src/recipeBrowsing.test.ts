import {describe,it,expect} from "vitest";
import {browseRecipes,defaultRecipeBrowse,searchText,recipeHasImage} from "./recipeBrowsing";
import type {Recipe} from "./api/recipeTypes";
const make=(id:string,name:string,scope:Recipe["scope"],source:string,count:number,date:string,meal:"lunch"|"dinner"):Recipe=>({id,name,scope,source,ingredients:Array(count).fill({}),updated_at:date,suitable_meal_types:[meal]}) as Recipe;
const rows=[make("shared","Arroz","shared","catalog",2,"2026-11-17","lunch"),make("family","Sopa","family","user",4,"2026-11-19","dinner"),make("edited","Batata","family","family_adaptation",3,"2026-11-18","dinner")];
describe("contextual recipe browsing",()=>{
 it("keeps adaptations separate from family originals and combines meal filters",()=>{
  expect(browseRecipes(rows,{...defaultRecipeBrowse,origin:"family"},"pt-PT").map(row=>row.id)).toEqual(["family"]);
  expect(browseRecipes(rows,{...defaultRecipeBrowse,origin:"adapted",meal:"dinner"},"pt-PT").map(row=>row.id)).toEqual(["edited"]);
  expect(browseRecipes(rows,{...defaultRecipeBrowse,origin:"shared",meal:"dinner"},"pt-PT")).toEqual([]);
 });
 it("orders without mutating server data",()=>{
  expect(browseRecipes(rows,{...defaultRecipeBrowse,sort:"updated"},"pt-PT").map(row=>row.id)).toEqual(["family","edited","shared"]);
  expect(browseRecipes(rows,{...defaultRecipeBrowse,sort:"ingredients"},"pt-PT").map(row=>row.id)).toEqual(["shared","edited","family"]);
  expect(rows[0]!.id).toBe("shared");
 });
 it("filters only images matching the actual recipe, preserving family suffix matches",()=>{
  const illustrated={...rows[2]!,name:"Frango rápido · família",image_url:null};
  const missing={...rows[1]!,name:"Receita sem fotografia",image_url:null};
  expect(recipeHasImage(illustrated)).toBe(true);
  expect(recipeHasImage(missing)).toBe(false);
  expect(browseRecipes([illustrated,missing],{...defaultRecipeBrowse,image:"without"},"pt-PT").map(row=>row.id)).toEqual(["family"]);
  expect(browseRecipes([illustrated,missing],{...defaultRecipeBrowse,image:"with"},"pt-PT").map(row=>row.id)).toEqual(["edited"]);
 });
 it("matches accents and surrounding whitespace in editor search",()=>{expect(searchText("  Açúcar  ")).toBe("acucar");});
});
