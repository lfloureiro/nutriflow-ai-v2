import {useState} from "react";

import type {ShoppingList,ShoppingListItem} from "./api/pantryShoppingTypes";

import {receiveShoppingItem} from "./api/pantryShoppingClient";

import {useI18n} from "./i18n";



export default function ShoppingReceiptEntry({familyId,item,onChanged,disabled}:{familyId:string;item:ShoppingListItem;onChanged:(data:ShoppingList)=>void;disabled:boolean}) {

  const {locale}=useI18n();const pt=locale==="pt-PT";

  const [quantity,setQuantity]=useState("");const [unit,setUnit]=useState(item.unit??"g");

  const [location,setLocation]=useState("");const [expiry,setExpiry]=useState("");

  const [reviewed,setReviewed]=useState(false);const [busy,setBusy]=useState(false);const [error,setError]=useState("");

  if(item.pantry_receipt) return <div className="shopping-receipt"><strong>{pt?"Recebido na despensa":"Received into pantry"}</strong><p>{Number(item.pantry_receipt.quantity).toLocaleString(locale)} {item.pantry_receipt.unit}{item.pantry_receipt.location?` · ${item.pantry_receipt.location}`:""}{item.pantry_receipt.expires_at?` · ${pt?"Validade":"Expiry"}: ${new Date(item.pantry_receipt.expires_at).toLocaleDateString(locale)}`:""}</p><small>{pt?"Entrada registada. Ajuste quantidades e validade na despensa.":"Receipt recorded. Adjust quantities and expiry in the pantry."}</small></div>;

  if(item.status!=="purchased") return null;

  if(!item.food_item_id) return <p className="shopping-receipt">{pt?"Artigo livre: registe o ingrediente e a quantidade na despensa.":"Free text item: record the ingredient and quantity in the pantry."}</p>;

  async function submit(event:React.FormEvent) {

    event.preventDefault();setBusy(true);setError("");

    try {onChanged(await receiveShoppingItem(familyId,item.id,{expected_version:item.version??1,quantity,unit,location:location||null,expires_at:expiry?new Date(`${expiry}T23:59:59`).toISOString():null,label_reviewed:true}));}

    catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}

  }

  return <details className="shopping-receipt"><summary>{pt?"Registar o que chegou à despensa":"Record what arrived in the pantry"}</summary>

    <form onSubmit={e=>void submit(e)}>

      <p>{pt?"Indique a quantidade total recebida, incluindo as embalagens extra. Só esta confirmação adiciona stock.":"Enter the total received, including extra packages. Only this confirmation adds stock."}</p>

      <div className="two-column-fields">

        <label className="field"><span>{pt?"Quantidade recebida":"Quantity received"}</span><input type="number" min="0.0001" step="0.0001" required value={quantity} onChange={e=>setQuantity(e.target.value)}/></label>

        <label className="field"><span>{pt?"Unidade recebida":"Received unit"}</span><input required maxLength={24} value={unit} onChange={e=>setUnit(e.target.value)}/></label>

        <label className="field"><span>{pt?"Local de arrumação":"Storage location"}</span><input maxLength={80} value={location} onChange={e=>setLocation(e.target.value)}/></label>

        <label className="field"><span>{pt?"Validade (opcional)":"Expiry (optional)"}</span><input type="date" value={expiry} onChange={e=>setExpiry(e.target.value)}/></label>

      </div>

      <label><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/> {pt?"Confirmei o ingrediente, o rótulo e a quantidade que recebi.":"I checked the ingredient, label and quantity received."}</label>

      {error&&<p role="alert">{error}</p>}

      <button className="button small" type="submit" disabled={disabled||busy||!reviewed||!quantity}>{busy?(pt?"A registar…":"Recording…"):(pt?"Adicionar à despensa":"Add to pantry")}</button>

    </form>

  </details>;

}
