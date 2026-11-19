import type {PantryLot} from "./api/pantryShoppingTypes";
export type PantryState="available"|"soon"|"expired"|"undated"|"inactive"|"empty";
export function pantryState(lot:PantryLot,now:number):PantryState {
 if(!lot.is_available)return "inactive";
 const quantity=Number(lot.quantity_available);
 if(lot.quantity_available.trim()&&Number.isFinite(quantity)&&quantity<=0)return "empty";
 const expiry=lot.expires_at ? Date.parse(lot.expires_at) : NaN;
 if(!Number.isFinite(expiry))return "undated";
 if(expiry<now)return "expired";
 return expiry-now<=3*86400000?"soon":"available";
}
export function visiblePantryLots(lots:PantryLot[],query:string,filter:"all"|"soon"|"undated",now:number):PantryLot[] {
 const term=query.trim().toLocaleLowerCase();
 return lots.filter(lot=>`${lot.food_item_name} ${lot.location??""}`.toLocaleLowerCase().includes(term)&&(filter==="all" || (filter==="soon" ? ["soon","expired"].includes(pantryState(lot,now)) : pantryState(lot,now)==="undated"))).map((lot,index)=>({lot,index})).sort((a,b)=>{
 const rank=(lot:PantryLot)=>({expired:0,soon:1,available:2,undated:3,empty:4,inactive:5})[pantryState(lot,now)];
 return rank(a.lot)-rank(b.lot) || (Date.parse(a.lot.expires_at??"")-Date.parse(b.lot.expires_at??"") || a.index-b.index);
 }).map(row=>row.lot);
}
