import {describe,it,expect,vi} from "vitest";
import {renderToStaticMarkup} from "react-dom/server";
import WeekOverview,{weekOverview} from "./ui/WeekOverview";
import RecipeAdaptationCards from "./RecipeAdaptationCards";
import type {FamilyMealPlan,MealPlanEntry} from "./api/mealPlanTypes";
import type {ReviewRecipe} from "./api/dietaryReviewClient";
vi.mock("./i18n",()=>({useI18n:()=>({locale:"pt-PT"})}));
const entry=(id:string,status="planned"):MealPlanEntry=>({id,status,meal_type:"dinner",title:"Synthetic",scheduled_at:"2026-11-18T20:00:00Z",local_time:"20:00",recipe_id:"recipe",recipe_name:"Synthetic",location:null,notes:null,transformations:[],participants:[]});
const plan:FamilyMealPlan={family_id:"family",family_name:"Synthetic",timezone:"Europe/Lisbon",start_date:"2026-11-16",end_date:"2026-11-22",days:[{date:"2026-11-18",slots:[{meal_type:"breakfast",meals:[]},{meal_type:"lunch",meals:[entry("a"),entry("b")]},{meal_type:"snack",meals:[entry("c","cancelled")]},{meal_type:"dinner",meals:[{...entry("d"),variant_changes:["old → new"]}]}]}]};
describe("Weekly UX with persisted planning data",()=>{
 it("counts occupied slots separately from multiple groups and ignores cancellations",()=>{expect(weekOverview(plan)).toEqual({occupied:2,events:3,adapted:1,total:4,empty:2});});
 it("distinguishes proposals from saved plans and never presents coverage as suitability",()=>{const html=renderToStaticMarkup(<WeekOverview plan={plan} proposed={1}/>);expect(html).toContain("2/4");expect(html).toContain("em proposta");expect(html).toContain("A adequação é verificada por pessoa e porção");expect(html).not.toContain("100%");});
 it("shows missing substitution quantity rather than inventing a one-to-one replacement",()=>{
  const recipes:ReviewRecipe[]=[{id:"recipe",name:"Synthetic",source:"test",assessment_status:"not_evaluated",ingredients:[{id:"ingredient",food_item_id:"food",name:"Base ingredient",quantity:"200",unit:"g",references:[],substitutions:[{id:"option",recipe_ingredient_id:"ingredient",replacement_name:"Alternative ingredient",replacement_food_item_id:null,replacement_quantity:null,replacement_unit:null,reference_id:null,status:"proposed",notes:"Source incomplete",version:1}]}]}];
  const html=renderToStaticMarkup(<RecipeAdaptationCards recipes={recipes} excluded={["food"]} products={[]} restrictions={{sources:[],excluded_food_item_ids:[],warnings:[]}} people={[]} compact includeProposals/>);
  expect(html).toContain("Receita base");expect(html).toContain("Base ingredient");expect(html).toContain("Alternative ingredient");expect(html).toContain("Quantidade por confirmar");expect(html).toContain("Quantidades para a receita inteira");expect(html).not.toContain("200 g</span></div></div>");
 });
});
