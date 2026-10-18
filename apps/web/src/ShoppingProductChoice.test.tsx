import {afterEach,describe,expect,it,vi} from "vitest";
import {renderToStaticMarkup} from "react-dom/server";
import ShoppingProductChoice,{matchingConfirmedProduct} from "./ShoppingProductChoice";
import RetailAlternativeCards from "./RetailAlternativeCards";
import {previewShoppingProduct,selectShoppingProduct} from "./api/pantryShoppingClient";
import {retailActionError} from "./retailMessages";
import type {RetailAlternative} from "./api/planningWorkspaceClient";
import type {ShoppingListItem} from "./api/pantryShoppingTypes";
vi.mock("./i18n",()=>({useI18n:()=>({locale:"pt-PT"})}));
afterEach(()=>vi.unstubAllGlobals());
const product={alternative_group:"rice-corn-pasta",notes:"",id:"p",name:"Massa de arroz",retailer:"Loja",pack_quantity:"500",pack_unit:"g",product_url:"https://example.com/product",observed_price:"1.75",observed_on:"2026-10-18",ingredient_summary:"Arroz",evidence_level:"retailer_ingredients_and_nutrition",evidence_fingerprint:"a".repeat(64),nutrition_per_100:{reference_unit:"g",energy_kcal:"360",protein_g:"5",carbohydrate_g:"81",fat_g:"1"},applicable_food_item_ids:["wheat"]} as RetailAlternative;
const item={id:"i",food_item_id:"rice",name:"Massa de arroz",quantity:"1100",unit:"g",status:"needed",item_source:"automatic",version:3,sort_order:0,notes:null} as ShoppingListItem;
describe("exact product shopping",()=>{
 it("does not equate a proposed substitute with a confirmed actual ingredient",()=>{
   expect(matchingConfirmedProduct([product],"wheat")).toBeUndefined();
   expect(matchingConfirmedProduct([{...product,confirmed_food_item_id:"rice"}],"rice")?.id).toBe("p");
   expect(renderToStaticMarkup(<ShoppingProductChoice familyId="f" item={item} products={[product]} onChanged={()=>{}} disabled={false}/>)).toBe("");
 });
 it("does not show an empty product-history panel for a purchase without a selected product",()=>{
   expect(renderToStaticMarkup(<ShoppingProductChoice familyId="f" item={{...item,status:"purchased"}} products={[{...product,confirmed_food_item_id:"rice"}]} onChanged={()=>{}} disabled={false}/>)).toBe("");
 });
 it("does not expose a stale package count as an active choice",()=>{
   const stale={...item,product_selection:{product_name:"Massa de arroz",retailer:"Loja",product_url:product.product_url,observed_on:"2026-10-18",observed_price:"1.75",pack_quantity:"500",pack_unit:"g",required_quantity:"1100",required_unit:"g",package_count:null,total_quantity:null,excess_quantity:null,estimated_total:null,status:"needs_review" as const,issues:["quantity_changed"]}};
   const html=renderToStaticMarkup(<ShoppingProductChoice familyId="f" item={stale} products={[]} onChanged={()=>{}} disabled={false}/>);
   expect(html).toContain("precisa de revisão");expect(html).not.toContain("3 embalagens");
 });
 it("requires label review and usable evidence before offering ingredient creation",()=>{
   const available=renderToStaticMarkup(<RetailAlternativeCards familyId="f" products={[product]}/>);
   expect(available).toContain("Revi os ingredientes");expect(available).toContain("disabled");
   const incomplete=renderToStaticMarkup(<RetailAlternativeCards familyId="f" products={[{...product,ingredient_confirmation_issue:"complete_label_required"}]}/>);
   expect(incomplete).toContain("Falta confirmar o rótulo completo");expect(incomplete).not.toContain("Criar ingrediente deste produto");
 });
 it("separates preview requests from persistence and sends the current version",async()=>{
   const fetchMock=vi.fn().mockResolvedValue({ok:true,json:async()=>({})});vi.stubGlobal("fetch",fetchMock);
   const payload={expected_version:3,retail_product_id:"p",expected_fingerprint:"a".repeat(64)};
   await previewShoppingProduct("f","i",payload);await selectShoppingProduct("f","i",payload);
   expect(fetchMock.mock.calls[0]?.[0]).toContain("/product-preview");expect(fetchMock.mock.calls[0]?.[1]?.method).toBe("POST");
   expect(fetchMock.mock.calls[1]?.[1]?.method).toBe("PUT");expect(JSON.parse(fetchMock.mock.calls[1]?.[1]?.body)).toEqual(payload);
 });
 it("makes stale shopping and incompatible units actionable in Portuguese",()=>{
   expect(retailActionError(new Error("Refresh shopping to use current effective ingredient quantities"),true)).toContain("Atualiza a lista");
   expect(retailActionError(new Error("Package and ingredient units are incompatible"),true)).toContain("não foi assumida uma densidade");
 });
});
