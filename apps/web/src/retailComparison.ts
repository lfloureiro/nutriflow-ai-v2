import type {RetailAlternative} from "./api/planningWorkspaceClient";

// A commercial group is discovery context, never ingredient or clinical equivalence.
export function relatedRetailAlternatives(products:RetailAlternative[],foodId:string|null,selectedProductUrl?:string):RetailAlternative[] {
  if(!foodId)return [];
  const groups=new Set(products.filter(p=>p.applicable_food_item_ids.includes(foodId)||p.confirmed_food_item_id===foodId||p.product_url===selectedProductUrl).map(p=>p.alternative_group));
  return products.filter(p=>groups.has(p.alternative_group));
}
export function comparisonGroups(products:RetailAlternative[]) {
  const groups=new Map<string,{category:string;unit:"kg"|"l"|null;products:RetailAlternative[]}>();
  for(const p of products){const unit=p.price_comparison?.reference_unit??null;const key=JSON.stringify([p.alternative_group,unit]);
    if(!groups.has(key))groups.set(key,{category:p.alternative_group,unit,products:[]});
    groups.get(key)!.products.push(p);
  }
  for(const group of groups.values())group.products.sort((a,b)=>{
    const price=(p:RetailAlternative)=>p.price_comparison?.unit_price!=null&&!p.price_comparison.issue?Number(p.price_comparison.unit_price):Infinity;
    return price(a)-price(b)||a.retailer.localeCompare(b.retailer)||a.name.localeCompare(b.name);
  });
  return [...groups.values()];
}
export function retailGroupLabel(group:string,pt:boolean) {
  const labels:Record<string,[string,string]>={
    "rice-corn-pasta":["Massas de arroz e milho","Rice and corn pasta"],
    "rice-corn-thickener":["Farinhas e espessantes","Flours and thickeners"],
    "lactose-free-cream":["Natas sem lactose","Lactose-free cream"],
    "lactose-free-milk":["Leite sem lactose","Lactose-free milk"],
    "lactose-free-yogurt":["Iogurte sem lactose","Lactose-free yogurt"],
    "chives-seasoning":["Cebolinho","Chives"],
  };
  return labels[group]?.[pt?0:1]??group.replaceAll("-"," ");
}
