import {afterEach,describe,expect,it,vi} from "vitest";
import {renderToStaticMarkup} from "react-dom/server";
import ShoppingReceiptEntry from "./ShoppingReceiptEntry";
import {receiveShoppingItem} from "./api/pantryShoppingClient";
import type {ShoppingListItem} from "./api/pantryShoppingTypes";
vi.mock("./i18n",()=>({useI18n:()=>({locale:"pt-PT"})}));
afterEach(()=>vi.unstubAllGlobals());
const item={id:"i",food_item_id:"f",name:"Arroz",quantity:"1100",unit:"g",status:"purchased",item_source:"automatic",notes:null,sort_order:0,version:4} as ShoppingListItem;
const html=(value:ShoppingListItem)=>renderToStaticMarkup(<ShoppingReceiptEntry familyId="family" item={value} onChanged={()=>{}} disabled={false}/>);
describe("shopping receipt",()=>{
 it("only offers receiving after purchase with an explicit empty quantity and label check",()=>{
   expect(html({...item,status:"needed"})).toBe("");
   const markup=html(item);expect(markup).toContain("Quantidade recebida");expect(markup).toContain("disabled");expect(markup).not.toContain('value="1100"');
 });
 it("keeps receipt visible without offering another stock entry",()=>{
   const markup=html({...item,pantry_receipt:{lot_id:"lot",quantity:"1500",unit:"g",location:"Armário",expires_at:null,received_at:"2030-01-01"}});
   expect(markup).toContain("1500");expect(markup).toContain("Recebido na despensa");expect(markup).not.toContain("<form");
 });
 it("does not guess an ingredient for a free text purchase",()=>{expect(html({...item,food_item_id:null})).not.toContain("<form");});
 it("posts actual received quantity and version separately from package selection",async()=>{
   const fetchMock=vi.fn().mockResolvedValue({ok:true,json:async()=>({})});vi.stubGlobal("fetch",fetchMock);
   const payload={expected_version:4,quantity:"1500",unit:"g",label_reviewed:true as const};
   await receiveShoppingItem("family","i",payload);
   expect(fetchMock.mock.calls[0]?.[0]).toContain("/items/i/receipt");expect(JSON.parse(fetchMock.mock.calls[0]?.[1]?.body)).toEqual(payload);
 });
});
