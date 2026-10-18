import {useRef,useState} from "react";
import type {ShoppingList,ShoppingListItem,ShoppingReceiptLot} from "./api/pantryShoppingTypes";
import {receiveShoppingBatch} from "./api/pantryShoppingClient";
import {useI18n} from "./i18n";

type LotDraft={key:number;quantity:string;unit:string;location:string;expiry:string};
export default function ShoppingReceiptEntry({familyId,item,onChanged,disabled}:{familyId:string;item:ShoppingListItem;onChanged:(data:ShoppingList)=>void;disabled:boolean}) {
  const {locale}=useI18n();const pt=locale==="pt-PT";
  const receipt=item.pantry_receipt;const partial=receipt?.status==="partial";
  const nextKey=useRef(1);
  const emptyLot=():LotDraft=>({key:nextKey.current++,quantity:"",unit:item.unit??"g",location:"",expiry:""});
  const [lots,setLots]=useState<LotDraft[]>(()=>[emptyLot()]);
  const [complete,setComplete]=useState(!partial);const [expected,setExpected]=useState("");
  const [reviewed,setReviewed]=useState(false);const [busy,setBusy]=useState(false);const [error,setError]=useState("");
  const attempt=useRef<{signature:string;id:string}|null>(null);
  const number=(v:string)=>Number(v).toLocaleString(locale,{maximumFractionDigits:4});
  const expiryText=(v:string|null|undefined)=>v?` · ${pt?"Validade":"Expiry"}: ${new Date(v).toLocaleDateString(locale)}`:"";
  if(!receipt&&item.status!=="purchased")return null;
  if(!item.food_item_id&&!receipt)return <p className="shopping-receipt">{pt?"Artigo livre: registe o ingrediente e a quantidade na despensa.":"Free text item: record the ingredient and quantity in the pantry."}</p>;
  function updateLot(key:number,field:keyof LotDraft,value:string){setLots(old=>old.map(l=>l.key===key?{...l,[field]:value}:l));}
  async function receive(closeOnly=false) {
    setBusy(true);setError("");
    try {
      const rows:ShoppingReceiptLot[]=closeOnly?[]:lots.map(l=>({quantity:l.quantity,unit:l.unit,location:l.location||null,expires_at:l.expiry?new Date(`${l.expiry}T23:59:59`).toISOString():null}));
      const values={lots:rows,complete:closeOnly||complete,expected_quantity:!receipt&&!complete?expected:null};
      const signature=JSON.stringify(values);
      if(attempt.current?.signature!==signature)attempt.current={signature,id:crypto.randomUUID()};
      const data=await receiveShoppingBatch(familyId,item.id,{...values,request_id:attempt.current.id,expected_version:item.version??1,label_reviewed:true});
      onChanged(data);setLots([emptyLot()]);setReviewed(false);attempt.current=null;
    }catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
  }
  return <div className="shopping-receipt">
    {receipt&&<div className="shopping-receipt-history">
      <strong>{partial?(pt?"Receção parcial · entrega pendente":"Partial receipt · delivery pending"):(pt?"Recebido na despensa":"Received into pantry")}</strong>
      <p>{number(receipt.quantity)} {receipt.unit} {pt?"recebidos":"received"}{receipt.location?` · ${receipt.location}`:""}{expiryText(receipt.expires_at)}</p>
      {receipt.expected_quantity&&<p>{number(receipt.expected_quantity)} {receipt.unit} {pt?"esperados nesta compra":"expected for this purchase"} · {number(receipt.remaining_quantity??"0")} {receipt.unit} {partial?(pt?"por receber":"still to arrive"):(pt?"não recebidos":"not received")}</p>}
      {!!receipt.batches?.length&&<details><summary>{pt?"Ver lotes e validades":"View lots and expiry dates"} ({receipt.batches.reduce((n,b)=>n+b.lots.length,0)})</summary><ul>{receipt.batches.flatMap(b=>b.lots.map((l,i)=><li key={`${b.request_id}:${i}`}>{number(l.quantity)} {l.unit}{l.location?` · ${l.location}`:""}{expiryText(l.expires_at)} · {pt?"Recebido em":"Received on"}: {new Date(b.received_at).toLocaleDateString(locale)}</li>))}</ul></details>}
      <small>{pt?"Entradas registadas. Corrija saldos e validade nos lotes da despensa; o histórico conserva o que foi recebido.":"Receipts recorded. Correct balances and expiry in pantry lots; history preserves what was received."}</small>
    </div>}
    {(!receipt||partial)&&<details open={partial||undefined}><summary>{partial?(pt?"Registar a próxima entrega":"Record the next delivery"):(pt?"Registar o que chegou à despensa":"Record what arrived in the pantry")}</summary>
      <form onSubmit={e=>{e.preventDefault();void receive();}}>
        <p>{pt?"Registe apenas o que chegou agora. Separe os lotes quando a validade ou o local forem diferentes.":"Record only what arrived now. Separate lots with different expiry dates or storage locations."}</p>
        <fieldset disabled={disabled||busy} className="shopping-delivery-fields">
          {lots.map((lot,index)=><div className="shopping-delivery-lot" key={lot.key}>
            <strong>{pt?"Lote":"Lot"} {index+1}</strong>
            <div className="two-column-fields">
              <label className="field"><span>{pt?"Quantidade recebida":"Quantity received"} · {index+1}</span><input type="number" min="0.0001" step="0.0001" required value={lot.quantity} onChange={e=>updateLot(lot.key,"quantity",e.target.value)}/></label>
              <label className="field"><span>{pt?"Unidade recebida":"Received unit"} · {index+1}</span><input required maxLength={24} value={lot.unit} onChange={e=>updateLot(lot.key,"unit",e.target.value)}/></label>
              <label className="field"><span>{pt?"Local de arrumação":"Storage location"} · {index+1}</span><input maxLength={80} value={lot.location} onChange={e=>updateLot(lot.key,"location",e.target.value)}/></label>
              <label className="field"><span>{pt?"Validade (opcional)":"Expiry (optional)"} · {index+1}</span><input type="date" value={lot.expiry} onChange={e=>updateLot(lot.key,"expiry",e.target.value)}/></label>
            </div>
            {lots.length>1&&<button className="button ghost small" type="button" onClick={()=>setLots(old=>old.filter(l=>l.key!==lot.key))}>{pt?"Remover lote":"Remove lot"} {index+1}</button>}
          </div>)}
          <button className="button ghost small" type="button" disabled={lots.length>=20} onClick={()=>setLots(old=>[...old,emptyLot()])}>{pt?"Adicionar lote com outra validade/local":"Add lot with another expiry/location"}</button>
          <label><input type="checkbox" checked={complete} onChange={e=>setComplete(e.target.checked)}/> {pt?"Esta receção conclui a compra: não vai chegar mais.":"This receipt completes the purchase: nothing else will arrive."}</label>
          {!complete&&!receipt&&<label className="field"><span>{pt?"Total esperado nesta compra":"Total expected for this purchase"} ({item.unit})</span><input type="number" min="0.0001" step="0.0001" required value={expected} onChange={e=>setExpected(e.target.value)}/></label>}
          {!complete&&<p className="muted">{pt?"O restante fica previsto por receber; não conta como stock disponível.":"The remainder stays expected; it does not count as available stock."}</p>}
          <label><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/> {pt?"Confirmei o ingrediente, o rótulo e as quantidades que recebi agora.":"I checked the ingredient, label and quantities received now."}</label>
          <button className="button small" type="submit" disabled={!reviewed||lots.some(l=>!l.quantity)||(!complete&&!receipt&&!expected)}>{busy?(pt?"A registar…":"Recording…"):(pt?"Adicionar à despensa":"Add to pantry")}</button>
          {partial&&<button className="button ghost small" type="button" onClick={()=>void receive(true)}>{pt?"Concluir sem receber mais":"Complete without receiving more"}</button>}
        </fieldset>
      </form>
    </details>}
    {error&&<p role="alert">{error}</p>}
  </div>;
}
