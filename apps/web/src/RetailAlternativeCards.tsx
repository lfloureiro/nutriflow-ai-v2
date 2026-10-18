import {retailActionError} from "./retailMessages";
import {useEffect,useRef,useState} from "react";
import {confirmRetailIngredient,type RetailAlternative} from "./api/planningWorkspaceClient";
import {useI18n} from "./i18n";

export function retailEvidenceLabel(level:string,pt:boolean):string {
  if(level==="retailer_ingredients_and_nutrition")return pt?"Ingredientes e nutrição publicados":"Ingredients and nutrition published";
  if(level==="retailer_ingredients_only")return pt?"Ingredientes publicados · nutrição por confirmar":"Ingredients published · nutrition unconfirmed";
  return pt?"Rótulo completo por confirmar":"Full label unconfirmed";
}
export default function RetailAlternativeCards({products,familyId,onConfirmed}:{products:RetailAlternative[];familyId?:string;onConfirmed?:()=>void}){
  const {locale}=useI18n();const pt=locale==="pt-PT";
  const [reviewed,setReviewed]=useState<Record<string,boolean>>({});
  const [confirmed,setConfirmed]=useState<Record<string,string>>({});
  const [busy,setBusy]=useState("");const [error,setError]=useState("");const generation=useRef(0);
  useEffect(()=>{generation.current++;setReviewed({});setConfirmed({});setError("");setBusy("");return()=>{generation.current++;};},[familyId]);
  async function confirm(product:RetailAlternative){
    if(!familyId)return;const current=generation.current;setBusy(product.id);setError("");
    try{const result=await confirmRetailIngredient(familyId,product);if(current!==generation.current)return;setConfirmed(old=>({...old,[`${product.id}:${product.evidence_fingerprint}`]:result.food_item_id}));onConfirmed?.();}
    catch(e){if(current===generation.current)setError(retailActionError(e,pt));}finally{if(current===generation.current)setBusy("");}
  }
  if(!products.length)return null;
  return <div className="retail-alternatives">
    <strong>{pt?"Alternativas de supermercado para rever":"Supermarket alternatives to review"}</strong>
    <p className="muted">{pt?"Escolher um produto diferente exige rever a receita e a porção. Confirmar o rótulo cria um ingrediente próprio; não aplica a substituição nem certifica a porção FODMAP.":"A different product requires reviewing the recipe and portion. Confirming a label creates a separate ingredient; it does not apply a swap or certify a FODMAP serving."}</p>
    {error&&<p role="alert">{error}</p>}
    {products.map(p=>{const available=confirmed[`${p.id}:${p.evidence_fingerprint}`]??p.confirmed_food_item_id;return <article className="retail-alternative" key={p.id}>
      <div><span className="eyebrow">{p.retailer}</span><h4>{p.name}</h4><p>{Number(p.pack_quantity).toLocaleString(locale)} {p.pack_unit}{p.observed_price!==null?` · ${Number(p.observed_price).toLocaleString(locale,{style:"currency",currency:"EUR"})}`:""}</p></div>
      <p>{p.ingredient_summary}</p><span className="dietary-badge">{retailEvidenceLabel(p.evidence_level,pt)}</span>
      {p.nutrition_per_100&&<p>{pt?"Por 100":"Per 100"} {p.nutrition_per_100.reference_unit}: {p.nutrition_per_100.energy_kcal} kcal · {p.nutrition_per_100.protein_g} g {pt?"proteína":"protein"}</p>}
      <p className="muted">{pt?"Consultado em":"Checked"} {p.observed_on} · {pt?"Preço e stock a confirmar. Não certificado FODMAP por porção.":"Confirm current price and stock. Not FODMAP certified per serving."}</p>
      <a className="button secondary small" href={p.product_url} target="_blank" rel="noreferrer">{pt?"Ver produto e rótulo na loja ↗":"View product and label at store ↗"}</a>
      {familyId&&(available?<p role="status">{pt?"Ingrediente disponível. Usa «Atualizar ingredientes» no editor de variantes, escolhe este produto e define a quantidade da receita.":"Ingredient available. Use Refresh ingredients in the variant editor, select this product and specify its recipe quantity."}</p>:p.evidence_fingerprint&&!p.ingredient_confirmation_issue?<div className="retail-confirmation"><label><input type="checkbox" checked={!!reviewed[p.id]} disabled={!!busy} onChange={e=>setReviewed(old=>({...old,[p.id]:e.target.checked}))}/>{pt?"Revi os ingredientes, alergénios e a informação nutricional deste rótulo.":"I reviewed this label's ingredients, allergens and nutrition."}</label><button type="button" className="button secondary small" disabled={!!busy||!reviewed[p.id]} onClick={()=>void confirm(p)}>{busy===p.id?pt?"A guardar…":"Saving…":pt?"Criar ingrediente deste produto":"Create ingredient from this product"}</button></div>:<p>{pt?"Falta confirmar o rótulo completo e a nutrição para criar um ingrediente utilizável.":"Complete usable label and nutrition are required before creating an ingredient."}</p>)}
    </article>;})}
  </div>;
}
