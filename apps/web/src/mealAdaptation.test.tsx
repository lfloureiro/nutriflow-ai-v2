import {describe,it,expect,vi} from "vitest";
import {renderToStaticMarkup} from "react-dom/server";
import {adaptationMissingData,operationWithSource,recipeEditReady,draftReady,initialPortion,suggestedOperation} from "./mealAdaptation";
import MealAdaptationFlow from "./MealAdaptationFlow";
import type {ReviewRecipe} from "./api/dietaryReviewClient";
import type {MealPlanEntry} from "./api/mealPlanTypes";
vi.mock("./i18n",()=>({useI18n:()=>({locale:"pt-PT"})}));
const recipe:ReviewRecipe={id:"base",name:"Synthetic",source:"test",assessment_status:"not_evaluated",serving_count:"2",ingredients:[{id:"ingredient",food_item_id:"old",name:"Original",quantity:"100",unit:"g",references:[],substitutions:[{id:"sub",recipe_ingredient_id:"ingredient",replacement_name:"Alternative",replacement_food_item_id:null,replacement_quantity:null,replacement_unit:null,status:"proposed",reference_id:null,notes:"",version:1}]}]};
describe("ingredient acceptance followed by meal confirmation",()=>{
 it("keeps textual alternatives unidentified and prefills editable original amounts",()=>{const op=suggestedOperation(recipe,"ingredient");expect(op.replacement_food_item_id).toBe("");expect(op.quantity).toBe("100");expect(op.unit).toBe("g");expect(op.preparation).toBe("");});
 it("never reuses grams as servings when adapting a meal",()=>{const entry={participants:[{person_id:"person",quantity:"300",unit:"g"}]} as MealPlanEntry;expect(initialPortion(entry,"person")).toBe("");expect(initialPortion(null,"person",[{person_id:"person",quantity:"300",unit:"g"}])).toBe("");expect(initialPortion(null,"person",[{person_id:"person",quantity:"1.5",unit:"serving"}])).toBe("1.5");});
 it("requires identified changes, confirmed yield and positive servings for every attendee",()=>{const op={recipe_ingredient_id:"ingredient",replacement_food_item_id:"new",quantity:"100",unit:"g",preparation:"cozido"};expect(draftReady("2",[op],{a:"1",b:"1"},["a","b"])).toBe(true);expect(draftReady("2",[op],{a:"1",b:""},["a","b"])).toBe(false);expect(draftReady("2",[{...op,quantity:""}],{a:"1"},["a"])).toBe(false);expect(draftReady("2",[op],{a:"-1"},["a"])).toBe(false);});
 it("makes the three steps visible before opening the editor",()=>{const html=renderToStaticMarkup(<MealAdaptationFlow familyId="family" recipe={recipe} context={{recipeId:"base",planningDate:"2026-11-18",mealType:"dinner",personIds:["person"],appliedChanges:[]}} people={[{id:"person",first_name:"Test"}]} excluded={[]} onVariantsChanged={()=>{}}/>);expect(html).toContain("1. Rever propostas");expect(html).toContain("2. Rever receita");expect(html).toContain("3. Confirmar refeição");expect(html).toContain("Preparar as trocas");expect(html).not.toContain("Trocas aceites.");});
});

it("explains inherited missing yield separately from undefined replacement quantities",()=>{
 const base={...recipe,serving_count:null};const issues=adaptationMissingData(base,"",{ingredient:suggestedOperation(base,"ingredient")},{person:"1"},[{id:"person",first_name:"Test"}],true);
 expect(issues.some(issue=>issue.includes("não está registado na receita original"))).toBe(true);expect(issues.some(issue=>issue.includes("quantidade"))).toBe(false);expect(issues.some(issue=>issue.includes("catálogo"))).toBe(true);
});

it("inherits source units/counts without overwriting an explicit replacement or converting units",()=>{
 const source={...recipe,ingredients:[{...recipe.ingredients[0]!,quantity:"1",unit:"un",preparation:"diluído"}]};
 expect(suggestedOperation(source,"ingredient")).toMatchObject({quantity:"1",unit:"un",preparation:"diluído"});
 const proposal=source.ingredients[0]!.substitutions[0]!;
 expect(operationWithSource(source,"ingredient",{...proposal,replacement_quantity:"2",replacement_unit:"un"})).toMatchObject({quantity:"2",unit:"un"});
 expect(operationWithSource(source,"ingredient",{...proposal,replacement_unit:"g"})).toMatchObject({quantity:"",unit:"g"});
});

it("does not require optional preparation to complete an identified quantified adaptation",()=>{
 const op={recipe_ingredient_id:"ingredient",replacement_food_item_id:"food",quantity:"1",unit:"un",preparation:""};
 expect(draftReady("2",[op],{a:"1"},["a"])).toBe(true);
 expect(adaptationMissingData(recipe,"2",{ingredient:op},{a:"1"},[{id:"a",first_name:"A"}],true)).toEqual([]);
});

it("recipe edits inherit unknown yield, accepted descriptions and packaging units without new requirements",()=>{
 const operation={recipe_ingredient_id:"ingredient",replacement_food_item_id:"",quantity:"3",unit:"emb",preparation:""};
 expect(recipeEditReady("",[operation],{a:"1.5"},["a"])).toBe(true);
 expect(recipeEditReady("",[{...operation,quantity:""}],{a:"1"},["a"])).toBe(false);
 expect(recipeEditReady("-1",[operation],{a:"1"},["a"])).toBe(false);
});
