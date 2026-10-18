import {useI18n} from "./i18n";
export default function IngredientAlternativeLine({name,alternatives,quantity}:{name:string;alternatives:string[];quantity?:string}){
  const {locale}=useI18n();
  return <span className="ingredient-alternative-line"><strong>{name}{quantity?` · ${quantity}`:""}</strong>{alternatives.length>0 && <><span> → </span><strong className="ingredient-alternative-name">{alternatives.join(locale==="pt-PT"?" ou ":" or ")}</strong><small className="ingredient-alternative-status">{locale==="pt-PT"?"Proposta · por aplicar":"Proposed · not applied"}</small></>}</span>;
}
