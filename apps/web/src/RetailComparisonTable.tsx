import type {RetailAlternative} from "./api/planningWorkspaceClient";
import {comparisonGroups,retailGroupLabel} from "./retailComparison";
import {useI18n} from "./i18n";

export default function RetailComparisonTable({products,selectedProductId,onReview}:{products:RetailAlternative[];selectedProductId:string|null;onReview:(id:string)=>void}) {
  const {locale}=useI18n();const pt=locale==="pt-PT";
  const money=(v:string)=>Number(v).toLocaleString(locale,{style:"currency",currency:"EUR",maximumFractionDigits:4});
  return <section className="retail-comparison" aria-label={pt?"Comparar lojas":"Compare stores"}>
    <h4>{pt?"Comparar lojas e embalagens":"Compare stores and packages"}</h4>
    <p className="muted">{pt?"Ordenado pelo preço observado por kg/l dentro de cada grupo. As composições podem ser diferentes: reveja o rótulo e a receita. Preços de datas diferentes, descontos, entrega e stock não estão garantidos.":"Sorted by observed price per kg/l within each group. Compositions can differ: review the label and recipe. Prices from different dates, discounts, delivery and stock are not guaranteed."}</p>
    {comparisonGroups(products).map(group=><div className="retail-comparison-scroll" key={`${group.category}:${group.unit}`} tabIndex={0} role="region" aria-label={`${retailGroupLabel(group.category,pt)} · ${group.unit??(pt?"unidade por confirmar":"unit unconfirmed")}`}>
      <table><caption>{retailGroupLabel(group.category,pt)}{group.unit?` · €/${group.unit}`:""}</caption>
        <thead><tr><th scope="col">{pt?"Produto / loja":"Product / store"}</th><th scope="col">{pt?"Embalagem / preço":"Package / price"}</th><th scope="col">{group.unit?`€/${group.unit}`:(pt?"Preço unitário":"Unit price")}</th><th scope="col">{pt?"Observado em":"Observed on"}</th><th scope="col">{pt?"Revisão do rótulo":"Label review"}</th></tr></thead>
        <tbody>{group.products.map(p=><tr key={p.id} className={selectedProductId===p.id?"selected":""}>
          <th scope="row"><a href={p.product_url} target="_blank" rel="noreferrer">{p.name} ↗</a><small>{p.retailer}</small></th>
          <td>{Number(p.pack_quantity).toLocaleString(locale)} {p.pack_unit}<small>{p.observed_price!==null?money(p.observed_price):(pt?"Preço por confirmar":"Price unconfirmed")}</small></td>
          <td>{p.price_comparison?.unit_price!=null&&!p.price_comparison.issue?money(p.price_comparison.unit_price):"—"}</td>
          <td>{p.observed_on}</td>
          <td><small>{p.confirmed_food_item_id?(pt?"Ingrediente disponível":"Ingredient available"):p.ingredient_confirmation_issue||!p.evidence_fingerprint?(pt?"Informação incompleta":"Incomplete information"):(pt?"Informação para rever":"Information to review")}</small><button className="button ghost small" type="button" aria-pressed={selectedProductId===p.id} aria-label={`${pt?"Rever rótulo":"Review label"}: ${p.name}`} onClick={()=>onReview(p.id)}>{pt?"Rever rótulo":"Review label"}</button></td>
        </tr>)}</tbody>
      </table>
    </div>)}
  </section>;
}
