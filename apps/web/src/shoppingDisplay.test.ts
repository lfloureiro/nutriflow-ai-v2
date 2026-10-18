import {describe,expect,it} from "vitest";
import {orderedShoppingItems} from "./shoppingDisplay";
import type {ShoppingListItem} from "./api/pantryShoppingTypes";
const base={food_item_id:"food",name:"Arroz",quantity:"200",unit:"g",item_source:"automatic",notes:null,sort_order:0} as const;
const receipt={quantity:"500",unit:"g",received_at:"2030-01-01",status:"complete" as const};
describe("shopping task order",()=>{
 it("keeps new shortages first, incoming receipts next, and completed history last",()=>{
   const items:ShoppingListItem[]=[{...base,id:"history",status:"purchased",pantry_receipt:receipt},{...base,id:"partial",status:"purchased",pantry_receipt:{...receipt,status:"partial"}},{...base,id:"needed",status:"needed"},{...base,id:"bought",status:"purchased"}];
   expect(orderedShoppingItems(items).map(i=>i.id)).toEqual(["needed","partial","bought","history"]);
   expect(items[0]?.id).toBe("history");
 });
 it("preserves the server order within each group and treats legacy receipts as complete",()=>{
   const items:ShoppingListItem[]=[{...base,id:"legacy",status:"purchased",pantry_receipt:{quantity:"500",unit:"g",received_at:"2030-01-01"}},{...base,id:"a",status:"needed"},{...base,id:"b",status:"needed"}];
   expect(orderedShoppingItems(items).map(i=>i.id)).toEqual(["a","b","legacy"]);
 });
});
