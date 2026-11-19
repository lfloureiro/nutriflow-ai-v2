import {describe,it,expect,vi} from "vitest";
import {renderToStaticMarkup} from "react-dom/server";
import SubstitutionChoices,{proposalOperation,proposedIngredientIds} from "./SubstitutionChoices";
import type {ReviewRecipe} from "./api/dietaryReviewClient";
vi.mock("./i18n",()=>({useI18n:()=>({locale:"pt-PT"})}));
const proposal={id:"proposal",recipe_ingredient_id:"ingredient",replacement_name:"Suggested alternative",replacement_food_item_id:null,replacement_quantity:null,replacement_unit:null,status:"proposed" as const,reference_id:null,notes:"",version:1};
const recipe:ReviewRecipe={id:"recipe",name:"Synthetic",source:"test",assessment_status:"not_evaluated",ingredients:[{id:"ingredient",food_item_id:"base",name:"Base food",quantity:"1",unit:"un",references:[],substitutions:[proposal]}]};
const render=(decisions:{ingredient?:"accepted"|"ignored"})=>renderToStaticMarkup(<SubstitutionChoices recipe={recipe} foods={[]} excluded={[]} decisions={decisions} operations={decisions.ingredient==="accepted"?{ingredient:proposalOperation("ingredient",proposal)}:{}} onDecision={()=>{}} onContinue={()=>{}} disabled={false}/>);
describe("proposal-first recipe flow",()=>{
 it("starts with before/after proposals and actions, without the manual form",()=>{const html=render({});expect(html).toContain("Base food");expect(html).toContain("Suggested alternative");expect(html).toContain("Aceitar proposta");expect(html).toContain("Ignorar proposta");expect(html).toContain("Editar / escolher manualmente");expect(html).not.toContain('class="nf-manual-swap"');expect(html).toContain("1 propostas por decidir");});
 it("allows accepted textual proposals to advance for completion, without inventing details",()=>{const op=proposalOperation("ingredient",proposal);expect(op.replacement_food_item_id).toBe("");expect(op.quantity).toBe("");const html=render({ingredient:"accepted"});expect(html).toContain("dados em falta são completados");const button=html.match(/<button[^>]*>Rever receita com estas escolhas<\/button>/)?.[0];expect(button).toBeDefined();expect(button).not.toContain("disabled");});
 it("allows all proposals to be ignored before continuing with the original recipe",()=>{const html=render({ingredient:"ignored"});expect(html).toContain("mantém o ingrediente original");expect(html.match(/<button[^>]*>Rever receita com estas escolhas<\/button>/)?.[0]).not.toContain("disabled");});
 it("includes excluded ingredients but drops rejected standalone proposals",()=>{const changed={...recipe,ingredients:[{...recipe.ingredients[0]!,substitutions:[{...proposal,status:"rejected" as const}]}]};expect(proposedIngredientIds(changed,[])).toEqual([]);expect(proposedIngredientIds(changed,["base"])).toEqual(["ingredient"]);});
});

it("retains original quantity and unit for an accepted textual proposal without identifying another food",()=>{
 const operation=proposalOperation("ingredient",proposal,recipe);
 expect(operation).toMatchObject({replacement_food_item_id:"",quantity:"1",unit:"un"});
 const html=renderToStaticMarkup(<SubstitutionChoices recipe={recipe} foods={[]} excluded={[]} decisions={{ingredient:"accepted"}} operations={{ingredient:operation}} onDecision={()=>{}} onContinue={()=>{}} disabled={false}/>);
 expect(html).not.toContain('class="nf-manual-swap"');
 expect(html).toContain('1 un');
 expect(html.match(/<button[^>]*>Rever receita com estas escolhas<\/button>/)?.[0]).not.toContain('disabled');
});
