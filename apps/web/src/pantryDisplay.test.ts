import {describe,it,expect} from "vitest";
import {pantryState,visiblePantryLots} from "./pantryDisplay";
import type {PantryLot} from "./api/pantryShoppingTypes";
const now=Date.parse("2026-11-18T21:00:00Z");
const lot=(id:string,expires_at:string|null):PantryLot=>({id,family_id:"family",food_item_id:id,food_item_name:id,quantity_available:"100",unit:"g",location:"Frigorífico",expires_at,stock_key:id,observed_at:"",is_available:true,notes:null,created_at:"",updated_at:""});
describe("pantry expiry presentation",()=>{
 it("keeps unknown dates distinct from dated, soon and expired lots",()=>{
 expect(pantryState(lot("a",null),now)).toBe("undated");expect(pantryState(lot("a","invalid"),now)).toBe("undated");expect(pantryState(lot("a","2026-11-18T20:59:59Z"),now)).toBe("expired");expect(pantryState(lot("a","2026-11-21T21:00:00Z"),now)).toBe("soon");expect(pantryState(lot("a","2026-11-21T21:00:01Z"),now)).toBe("available");
 });
 it("does not show inactive or depleted lots as expiring stock",()=>{expect(pantryState({...lot("a",null),is_available:false},now)).toBe("inactive");expect(pantryState({...lot("a",null),quantity_available:"0"},now)).toBe("empty");});
 it("puts expired and soon lots first without merging or mutating batches",()=>{
 const rows=[lot("future","2026-12-01T23:00:00Z"),lot("old","2026-11-17T23:00:00Z"),lot("soon","2026-11-19T23:00:00Z"),lot("unknown",null)];expect(visiblePantryLots(rows,"","all",now).map(l=>l.id)).toEqual(["old","soon","future","unknown"]);expect(rows[0]?.id).toBe("future");expect(visiblePantryLots(rows,"","soon",now)).toHaveLength(2);
 });
 it("searches ingredient and storage location and filters missing dates",()=>{expect(visiblePantryLots([lot("Rice",null)],"frigor","undated",now)).toHaveLength(1);expect(visiblePantryLots([lot("Rice",null)],"Other","all",now)).toHaveLength(0);});
});
