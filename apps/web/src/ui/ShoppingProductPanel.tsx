import {useState} from "react";
import ShoppingProductChoice,{matchingConfirmedProduct} from "../ShoppingProductChoice";
import type {ShoppingList,ShoppingListItem} from "../api/pantryShoppingTypes";
import type {RetailAlternative} from "../api/planningWorkspaceClient";
import {useI18n} from "../i18n";
export default function ShoppingProductPanel(props:{familyId:string;item:ShoppingListItem;products:RetailAlternative[];onChanged:(list:ShoppingList)=>void;disabled:boolean}){
 const {locale}=useI18n();const pt=locale==="pt-PT";const [open,setOpen]=useState(false);const saved=props.item.product_selection;
 if(!saved&&!matchingConfirmedProduct(props.products,props.item.food_item_id))return null;
 return <details className="nf-shopping-product" onToggle={event=>setOpen(event.currentTarget.open)}><summary>{saved ? `${pt?"Embalagens: ":"Packages: "}${saved.product_name}` : (pt?"Escolher embalagens e loja":"Choose packages and store")}{saved?.status==="needs_review"&&<strong> · {pt?"Precisa de revisão":"Needs review"}</strong>}</summary>{open&&<ShoppingProductChoice {...props}/>}</details>;
}
