import {describe,expect,it,vi} from "vitest";
import {renderToStaticMarkup} from "react-dom/server";
import {comparisonGroups,relatedRetailAlternatives} from "./retailComparison";
import RetailComparisonTable from "./RetailComparisonTable";
import RetailAlternativeCards from "./RetailAlternativeCards";
import type {RetailAlternative} from "./api/planningWorkspaceClient";
vi.mock("./i18n",()=>({useI18n:()=>({locale:"pt-PT"})}));
const first={id:"a",name:"Massa Auchan",retailer:"Auchan",alternative_group:"rice-corn-pasta",product_url:"https://example.com/a",pack_quantity:"500",pack_unit:"g",observed_price:"1.75",observed_on:"2026-10-18",ingredient_summary:"Milho e arroz",evidence_level:"retailer_ingredients_and_nutrition",nutrition_per_100:null,notes:"",evidence_fingerprint:"a".repeat(64),ingredient_confirmation_issue:null,confirmed_food_item_id:"confirmed-rice",applicable_food_item_ids:["original-wheat","confirmed-rice"],price_comparison:{currency:"EUR",reference_unit:"kg",unit_price:"3.500000",issue:null}} as RetailAlternative;
const second={...first,id:"b",name:"Massa Continente",retailer:"Continente",product_url:"https://example.com/b",pack_quantity:"400",observed_price:"3.08",ingredient_summary:"Rótulo por confirmar",evidence_level:"retailer_description_only",confirmed_food_item_id:null,applicable_food_item_ids:["original-wheat"],ingredient_confirmation_issue:"complete_label_required",price_comparison:{currency:"EUR",reference_unit:"kg",unit_price:"7.700000",issue:null}} as RetailAlternative;
const unrelated={...first,id:"c",alternative_group:"lactose-free-milk",applicable_food_item_ids:["milk"],confirmed_food_item_id:null};
describe("retail comparison",()=>{
 it("keeps other stores visible for the exact confirmed ingredient without relabelling them as equivalent",()=>{
   expect(relatedRetailAlternatives([first,second,unrelated],"confirmed-rice").map(p=>p.id)).toEqual(["a","b"]);
   expect(second.applicable_food_item_ids).not.toContain("confirmed-rice");
   expect(relatedRetailAlternatives([first,second],"unknown")).toEqual([]);
   expect(relatedRetailAlternatives([first,second],null)).toEqual([]);
 });
 it("can retain discovery context for an historical selected product after its label changes",()=>{
   const stale={...first,confirmed_food_item_id:null,applicable_food_item_ids:[]};
   expect(relatedRetailAlternatives([stale,second],"old-confirmed",stale.product_url)).toHaveLength(2);
 });
 it("orders observed unit prices rather than incomparable package sizes and leaves missing prices last",()=>{
   const unknown={...first,id:"unknown",price_comparison:{currency:"EUR" as const,reference_unit:"kg" as const,unit_price:null,issue:"price_unavailable" as const}};
   const groups=comparisonGroups([second,unknown,first]);
   expect(groups[0]?.products.map(p=>p.id)).toEqual(["a","b","unknown"]);
 });
 it("never ranks volume against mass or mixes commercial categories",()=>{
   const volume={...first,id:"v",price_comparison:{currency:"EUR" as const,reference_unit:"l" as const,unit_price:"1",issue:null}};
   expect(comparisonGroups([first,volume,unrelated])).toHaveLength(3);
 });
 it("shows sources, observation dates and incomplete label coverage without a recipe-swap action",()=>{
   const html=renderToStaticMarkup(<RetailComparisonTable products={[first,second]} selectedProductId={null} onReview={()=>{}}/>);
   expect(html).toContain("€/kg");expect(html).toContain("Auchan");expect(html).toContain("Continente");expect(html).toContain("2026-10-18");expect(html).toContain("Informação incompleta");expect(html).toContain("composições podem ser diferentes");expect(html).not.toContain("Aplicar substituição");expect(html).toContain(first.product_url);
 });
 it("does not open every product label at once in a multi-product group",()=>{
   const html=renderToStaticMarkup(<RetailAlternativeCards familyId="f" products={[first,second]}/>);
   expect(html).toContain("Comparar lojas e embalagens");expect(html).not.toContain('class="retail-alternative"');expect(html).not.toContain("Revi os ingredientes");
 });
 it("still opens a lone product directly and requires explicit review",()=>{
   const html=renderToStaticMarkup(<RetailAlternativeCards familyId="f" products={[{...first,confirmed_food_item_id:null}]}/>);
   expect(html).toContain('class="retail-alternative"');expect(html).toContain("Revi os ingredientes");expect(html).toContain("disabled");expect(html).toContain("3,50");
 });
 it("does not turn an unknown unit price into zero",()=>{
   const html=renderToStaticMarkup(<RetailComparisonTable products={[{...first,observed_price:null,price_comparison:{currency:"EUR",reference_unit:"kg",unit_price:null,issue:"price_unavailable"}}]} selectedProductId={null} onReview={()=>{}}/>);
   expect(html).toContain("Preço por confirmar");expect(html).toContain("—");expect(html).not.toContain("0,00");
 });
});
