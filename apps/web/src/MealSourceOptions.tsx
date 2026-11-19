import {useEffect,useState} from "react";
import {getMealDiscoveryCapabilities} from "./api/setupClient";
import type {MealDiscoveryCapability} from "./api/setupTypes";
import {syncMealDeliveryProvider} from "./api/mealDeliveryClient";
import type {MealDeliveryMenuItem,MealDeliveryProviderKey} from "./api/mealDeliveryTypes";
import type {PlanningRestrictions} from "./api/planningWorkspaceClient";
import type {SelectedMealContext} from "./SelectedMealOptions";
import RestaurantDiscoveryScreen from "./RestaurantDiscoveryScreen";
import {useI18n} from "./i18n";

export const deliveryDestinations=[
  {key:"uber_eats",name:"Uber Eats",url:"https://www.ubereats.com/pt"},
  {key:"glovo",name:"Glovo",url:"https://glovoapp.com/pt/pt/"},
  {key:"bolt_food",name:"Bolt Food",url:"https://food.bolt.eu/"},
] as const;
export function providerCanSync(capability?:MealDiscoveryCapability){return !!(capability?.selected&&capability.live&&capability.supported);}
export default function MealSourceOptions({familyId,context,people,restrictions}:{familyId:string;context:SelectedMealContext;people:{id:string;first_name:string}[];restrictions:PlanningRestrictions}){
  const {locale}=useI18n();const pt=locale==="pt-PT";
  const [caps,setCaps]=useState<MealDiscoveryCapability[]>([]);const [error,setError]=useState("");
  const [busy,setBusy]=useState<string|null>(null);const [query,setQuery]=useState("");
  const [results,setResults]=useState<Partial<Record<MealDeliveryProviderKey,MealDeliveryMenuItem[]>>>({});
  const [showRestaurants,setShowRestaurants]=useState(false);
  useEffect(()=>{let cancelled=false;void getMealDiscoveryCapabilities(familyId).then(r=>{if(!cancelled)setCaps(r.capabilities);}).catch(e=>{if(!cancelled)setError(String(e));});return()=>{cancelled=true;};},[familyId]);
  async function sync(key:MealDeliveryProviderKey){setBusy(key);setError("");try{const r=await syncMealDeliveryProvider(familyId,key,query);setResults(old=>({...old,[key]:r.items}));}catch(e){setError(String(e));}finally{setBusy(null);}}
  return <details open={context.mealType==="lunch"} className="journey-card">
    <summary>{pt?"Entrega e restaurantes para esta refeição":"Delivery and restaurants for this meal"}</summary>
    <p>{context.planningDate} · {people.map(p=>p.first_name).join(" · ") || (pt?"Sem participantes":"No attendees")}</p>
    {restrictions.sources.map(s=><p key={s.source_id}><strong>{people.find(p=>p.id===s.person_id)?.first_name}: {s.label}</strong></p>)}
    <p>{pt?"Confirma ingredientes, molhos e preparação com o restaurante. Abrir a plataforma não envia as restrições nem guarda uma refeição no plano.":"Confirm ingredients, sauces and preparation with the restaurant. Opening a platform does not send restrictions or save a meal in the plan."}</p>
    {deliveryDestinations.some(p=>providerCanSync(caps.find(c=>c.source===p.key))) && <label className="field"><span>{pt?"O que procurar":"What to search for"}</span><input value={query} maxLength={160} onChange={e=>setQuery(e.target.value)}/></label>}
    <div className="adaptation-card-list">{deliveryDestinations.map(provider=>{
      const cap=caps.find(c=>c.source===provider.key);const ready=providerCanSync(cap);
      return <article key={provider.key} className="adaptation-base-card"><h4>{provider.name}</h4>
        <p>{ready?(pt?"Catálogo ligado":"Catalogue connected"):(pt?"Consulta na plataforma disponível. Importação automática por ligar.":"Platform browsing available. Automatic import is not connected.")}</p>
        <a className="button ghost" href={provider.url} target="_blank" rel="noreferrer">{pt?"Abrir":"Open"} {provider.name}</a>
        {ready && <button type="button" className="button primary" disabled={!!busy} onClick={()=>void sync(provider.key)}>{busy===provider.key?(pt?"A procurar…":"Searching…"):(pt?"Procurar pratos":"Find dishes")}</button>}
        {results[provider.key]?.map(item=><div key={item.catalog_key}><strong>{item.merchant_name} · {item.item_name}</strong><p>{item.description}</p><p>{item.item_price} {item.currency} · {pt?"Observado em":"Observed"} {item.observed_at}</p><p>{pt?"Ingredientes e adequação às restrições por confirmar; ainda não foi guardado no plano.":"Ingredients and suitability for restrictions remain unconfirmed; not saved in the plan."}</p></div>)}
        {context.onEvaluateDelivery && results[provider.key]?.some(item=>item.eligible_for_nutrition_ranking) && <button className="button primary" type="button" disabled={!!busy} onClick={()=>context.onEvaluateDelivery?.(provider.key)}>{pt?"Avaliar estes pratos para os presentes":"Evaluate these dishes for the attendees"}</button>}
        {results[provider.key]?.length===0 && <p>{pt?"Sem pratos encontrados nesta pesquisa.":"No dishes found for this search."}</p>}
      </article>;
    })}</div>
    {error && <p role="alert">{error}</p>}
    <button className="button ghost" type="button" onClick={()=>setShowRestaurants(v=>!v)}>{pt?"Procurar restaurantes nesta zona":"Find restaurants in this area"}</button>
    {showRestaurants && <RestaurantDiscoveryScreen embedded familyId={familyId}/>}
  </details>;
}
