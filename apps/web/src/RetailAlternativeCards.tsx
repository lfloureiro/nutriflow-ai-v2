import type { RetailAlternative } from "./api/planningWorkspaceClient";
import { useI18n } from "./i18n";

export function retailEvidenceLabel(level: string, pt: boolean): string {
  if (level === "retailer_ingredients_and_nutrition") return pt ? "Ingredientes e nutrição publicados" : "Ingredients and nutrition published";
  if (level === "retailer_ingredients_only") return pt ? "Ingredientes publicados · nutrição por confirmar" : "Ingredients published · nutrition unconfirmed";
  return pt ? "Rótulo completo por confirmar" : "Full label unconfirmed";
}

export default function RetailAlternativeCards({products}: {products: RetailAlternative[]}) {
  const {locale} = useI18n(); const pt = locale === "pt-PT";
  if (!products.length) return null;
  return <div className="retail-alternatives">
    <strong>{pt ? "Alternativas de supermercado para rever" : "Supermarket alternatives to review"}</strong>
    <p className="muted">{pt ? "Escolher um produto diferente pode exigir rever a receita e a porção. Estas sugestões não substituem automaticamente os ingredientes planeados." : "A different product may require reviewing the recipe and portion. Suggestions do not automatically replace planned ingredients."}</p>
    {products.map(p => <article className="retail-alternative" key={p.id}>
      <div><span className="eyebrow">{p.retailer}</span><h4>{p.name}</h4>
        <p>{Number(p.pack_quantity).toLocaleString(locale)} {p.pack_unit}
          {p.observed_price !== null ? ` · ${Number(p.observed_price).toLocaleString(locale, {style:"currency",currency:"EUR"})}` : ""}
        </p></div>
      <p>{p.ingredient_summary}</p>
      <span className="dietary-badge">{retailEvidenceLabel(p.evidence_level, pt)}</span>
      {p.nutrition_per_100 && <p>{pt ? "Por 100" : "Per 100"} {p.nutrition_per_100.reference_unit}: {p.nutrition_per_100.energy_kcal} kcal · {p.nutrition_per_100.protein_g} g {pt ? "proteína" : "protein"}</p>}
      <p className="muted">{pt ? "Consultado em" : "Checked"} {p.observed_on} · {pt ? "Preço e stock a confirmar na loja. Não certificado FODMAP para esta porção." : "Confirm current price and stock. Not FODMAP certified for this portion."}</p>
      <a className="button secondary small" href={p.product_url} target="_blank" rel="noreferrer">{pt ? "Ver produto e rótulo na loja ↗" : "View product and label at store ↗"}</a>
    </article>)}
  </div>;
}
