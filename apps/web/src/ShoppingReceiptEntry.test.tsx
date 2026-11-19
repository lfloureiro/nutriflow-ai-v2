import {afterEach,describe,expect,it,vi} from "vitest";
import {renderToStaticMarkup} from "react-dom/server";
import ShoppingReceiptEntry from "./ShoppingReceiptEntry";
import {receiveShoppingItem,receiveShoppingBatch} from "./api/pantryShoppingClient";
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


describe("partial and split receipts",()=>{
 const receipt={format_version:2,status:"partial" as const,quantity:"500",unit:"g",expected_quantity:"1500",remaining_quantity:"1000",received_at:"2030-01-07T10:00:00Z",batches:[{request_id:"r",received_at:"2030-01-07T10:00:00Z",complete:false,lots:[{lot_id:"one",quantity:"200",unit:"g",location:"A",expires_at:"2030-02-01T23:59:59Z"},{lot_id:"two",quantity:"300",unit:"g",location:"B",expires_at:"2030-03-01T23:59:59Z"}]}]};
 it("shows the received quantity and outstanding delivery separately with a next-delivery action",()=>{
   const markup=html({...item,pantry_receipt:receipt});
   expect(markup).toContain("Receção parcial");expect(markup).toContain("por receber");expect(markup).toContain("Registar a próxima entrega");expect(markup).toContain("não conta como stock");expect(markup).toContain("Concluir sem receber mais");
 });
 it("preserves separate lot locations and expiry dates after completion without another form",()=>{
   const markup=html({...item,pantry_receipt:{...receipt,status:"complete"}});
   expect(markup).toContain("Ver lotes e validades");expect(markup).toContain("200");expect(markup).toContain("300");expect(markup).toContain("Validade");expect(markup).not.toContain("<form");expect(markup).toContain("não recebidos");
 });
 it("offers explicit multiple lots without assuming the planned quantity was received",()=>{
   const markup=html(item);expect(markup).toContain("Adicionar lote com outra validade/local");expect(markup).toContain("não vai chegar mais");expect(markup).not.toContain('value="1100"');
 });
 it("sends stable request identity, separate lots and completion without using the legacy receipt endpoint",async()=>{
   const fetchMock=vi.fn().mockResolvedValue({ok:true,json:async()=>({})});vi.stubGlobal("fetch",fetchMock);
   const payload={request_id:"delivery",expected_version:4,lots:[{quantity:"500",unit:"g",location:"A",expires_at:null}],complete:false,expected_quantity:"1500",label_reviewed:true as const};
   await receiveShoppingBatch("family","i",payload);await receiveShoppingBatch("family","i",{...payload,lots:[],complete:true,expected_quantity:null});
   expect(fetchMock.mock.calls[0]?.[0]).toContain("/items/i/receipts");expect(JSON.parse(fetchMock.mock.calls[0]?.[1]?.body)).toEqual(payload);expect(JSON.parse(fetchMock.mock.calls[1]?.[1]?.body).lots).toEqual([]);
 });
});
