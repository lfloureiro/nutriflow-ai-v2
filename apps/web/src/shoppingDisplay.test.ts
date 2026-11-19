import {describe,expect,it} from "vitest";
import {orderedShoppingItems,shoppingOverview,visibleShoppingItems,shoppingPeriodChanged} from "./shoppingDisplay";
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

describe("shopping checklist stages",()=>{
 it("keeps purchased, partially received and completed receipts distinct",()=>{
 const items:ShoppingListItem[]=[{...base,id:"needed",status:"needed"},{...base,id:"bought",status:"purchased"},{...base,id:"partial",status:"purchased",pantry_receipt:{...receipt,status:"partial"}},{...base,id:"received",status:"purchased",pantry_receipt:receipt}];
 expect(shoppingOverview(items)).toEqual({all:4,needed:1,purchased:3,received:1,partial:1});
 expect(visibleShoppingItems(items,"received","").map(i=>i.id)).toEqual(["received"]);
 expect(visibleShoppingItems(items,"purchased","").map(i=>i.id)).toEqual(["bought","partial","received"]);
 });
 it("searches without changing source order or counting manual quantities as stock",()=>{
 const items:ShoppingListItem[]=[{...base,id:"milk",name:"Leite",status:"needed"},{...base,id:"rice",name:"Arroz",status:"needed"}];
 expect(visibleShoppingItems(items,"all"," LEI ").map(i=>i.id)).toEqual(["milk"]);expect(items).toHaveLength(2);expect(shoppingOverview(items).received).toBe(0);
 });
});

it("detects a changed requested interval without pretending the saved list was regenerated",()=>{
 const list={planning_start:"2026-11-16",planning_end:"2026-11-22"};
 expect(shoppingPeriodChanged(list,"2026-11-16",7)).toBe(false);expect(shoppingPeriodChanged(list,"2026-11-17",7)).toBe(true);expect(shoppingPeriodChanged(list,"2026-11-16",14)).toBe(true);expect(shoppingPeriodChanged(list,"",7)).toBe(true);expect(shoppingPeriodChanged({planning_start:null,planning_end:null},"2026-11-16",7)).toBe(false);
});
