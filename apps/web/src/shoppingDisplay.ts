import type {ShoppingList,ShoppingListItem} from "./api/pantryShoppingTypes";

// Keep actionable work above completed receipts without changing the API snapshot.
export function orderedShoppingItems(items:ShoppingListItem[]):ShoppingListItem[] {
  const priority=(item:ShoppingListItem)=>item.status==="needed"?0:!item.pantry_receipt||item.pantry_receipt.status==="partial"?1:2;
  return items.map((item,index)=>({item,index})).sort((a,b)=>priority(a.item)-priority(b.item)||a.index-b.index).map(row=>row.item);
}

export type ShoppingView = "all" | "needed" | "purchased" | "received";
export function receiptComplete(item:ShoppingListItem):boolean {return !!item.pantry_receipt && item.pantry_receipt.status!=="partial";}
export function shoppingOverview(items:ShoppingListItem[]) {
  return {all:items.length,needed:items.filter(i=>i.status==="needed").length,purchased:items.filter(i=>i.status==="purchased").length,received:items.filter(receiptComplete).length,partial:items.filter(i=>i.pantry_receipt?.status==="partial").length};
}
export function visibleShoppingItems(items:ShoppingListItem[],view:ShoppingView,query:string):ShoppingListItem[] {
  const term=query.trim().toLocaleLowerCase();
  return orderedShoppingItems(items).filter(item=>(view==="all" || (view==="received" ? receiptComplete(item) : item.status===view)) && item.name.toLocaleLowerCase().includes(term));
}

export function shoppingPeriodChanged(list:Pick<ShoppingList,"planning_start"|"planning_end">,startDate:string,days:number):boolean {
 if(!list.planning_start||!list.planning_end)return false;
 const start=Date.parse(startDate+"T12:00:00Z");
 if(!Number.isFinite(start)||!Number.isInteger(days)||days<1)return true;
 const end=new Date(start+(days-1)*86400000).toISOString().slice(0,10);
 return list.planning_start!==startDate || list.planning_end!==end;
}
