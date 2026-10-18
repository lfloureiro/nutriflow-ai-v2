import type {ShoppingListItem} from "./api/pantryShoppingTypes";

// Keep actionable work above completed receipts without changing the API snapshot.
export function orderedShoppingItems(items:ShoppingListItem[]):ShoppingListItem[] {
  const priority=(item:ShoppingListItem)=>item.status==="needed"?0:!item.pantry_receipt||item.pantry_receipt.status==="partial"?1:2;
  return items.map((item,index)=>({item,index})).sort((a,b)=>priority(a.item)-priority(b.item)||a.index-b.index).map(row=>row.item);
}
