import {retailActionError} from "./retailMessages";
import {useEffect,useState} from "react";
import {previewShoppingProduct,selectShoppingProduct} from "./api/pantryShoppingClient";
import type {ShoppingList,ShoppingListItem,ShoppingProductSelection} from "./api/pantryShoppingTypes";
import type {RetailAlternative} from "./api/planningWorkspaceClient";
import {useI18n} from "./i18n";

export function matchingConfirmedProduct(products:RetailAlternative[],foodId:string|null){
  return foodId?products.find(p=>p.confirmed_food_item_id===foodId):undefined;
}
export default function ShoppingProductChoice({familyId,item,products,onChanged,disabled}:{familyId:string;item:ShoppingListItem;products:RetailAlternative[];onChanged:(list:ShoppingList)=>void;disabled:boolean}){
  const {locale}=useI18n();const pt=locale==="pt-PT";
  const product=matchingConfirmedProduct(products,item.food_item_id);
  const [preview,setPreview]=useState<ShoppingProductSelection|null>(null);
  const [loading,setLoading]=useState(false);const [busy,setBusy]=useState(false);const [error,setError]=useState("");
  useEffect(()=>{let cancelled=false;setPreview(null);setError("");setLoading(false);
    if(!product?.evidence_fingerprint||!item.version||item.status!=="needed")return;
    setLoading(true);
    void previewShoppingProduct(familyId,item.id,{expected_version:item.version,retail_product_id:product.id,expected_fingerprint:product.evidence_fingerprint}).then(result=>{if(!cancelled)setPreview(result);}).catch(e=>{if(!cancelled)setError(retailActionError(e,pt));}).finally(()=>{if(!cancelled)setLoading(false);});
    return()=>{cancelled=true;};
  },[familyId,item.id,item.version,item.status,product?.id,product?.evidence_fingerprint]);
  async function choose(clear=false){if(!item.version)return;setBusy(true);setError("");try{onChanged(await selectShoppingProduct(familyId,item.id,{expected_version:item.version,retail_product_id:clear?null:product!.id,...(!clear?{expected_fingerprint:product!.evidence_fingerprint}:{})}));}catch(e){setError(retailActionError(e,pt));}finally{setBusy(false);}}
  if(!product&&!item.product_selection)return null;
  const saved=item.product_selection;const needsReview=saved?.status==="needs_review";
  const shown=needsReview?preview:saved??preview;
  const number=(value:string|number)=>Number(value).toLocaleString(locale,{maximumFractionDigits:4});
  return <section className="shopping-product-choice" aria-label={pt?"Produto e embalagens":"Product and packages"}>
    <h4>{saved&&!needsReview?pt?"Produto escolhido":"Selected product":pt?"Produto e embalagens para confirmar":"Product and packages to confirm"}</h4>
    {needsReview&&<p role="status">{pt?"A escolha anterior precisa de revisão. Atualiza as compras se a quantidade mudou; revê o rótulo e a variante se mudou o produto.":"The previous choice needs review. Refresh shopping if quantities changed; review the label and variant if the product changed."}</p>}
    {loading&&<p role="status">{pt?"A calcular embalagens…":"Calculating packages…"}</p>}
    {error&&<p role="alert">{error}</p>}
    {shown&&<><strong>{shown.product_name}</strong><p>{number(shown.required_quantity)} {shown.required_unit} {pt?"necessários":"needed"} · {number(shown.pack_quantity)} {shown.pack_unit} {pt?"por embalagem":"per package"}</p>
      {shown.package_count!==null&&<p><strong>{shown.package_count} {pt?"embalagens":"packages"}</strong> · {number(shown.total_quantity!)} {shown.pack_unit} {pt?"a comprar":"to buy"} · {number(shown.excess_quantity!)} {shown.pack_unit} {pt?"de excedente":"excess"}</p>}
      <p>{shown.estimated_total!==null?`${pt?"Estimativa":"Estimate"}: ${Number(shown.estimated_total).toLocaleString(locale,{style:"currency",currency:"EUR"})}`:pt?"Preço por confirmar":"Price unconfirmed"} · {shown.retailer} · {shown.observed_on}</p>
      <p className="muted">{pt?"Preço observado e stock por confirmar na loja. Escolher embalagens não altera a receita nem acrescenta stock à despensa.":"Observed price; confirm price and stock at the store. Choosing packages does not change the recipe or add pantry stock."}</p></>}
    {item.status==="needed"&&<div className="row-actions">{(!saved||needsReview)&&<button className="button secondary small" type="button" disabled={disabled||busy||loading||!preview||!product} onClick={()=>void choose()}>{pt?"Confirmar estas embalagens":"Confirm these packages"}</button>}{saved&&<button className="button ghost small" type="button" disabled={disabled||busy} onClick={()=>void choose(true)}>{pt?"Remover escolha do produto":"Clear product choice"}</button>}</div>}
  </section>;
}
