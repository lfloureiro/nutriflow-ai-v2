import {useState} from "react";
import {useI18n} from "../i18n";
import RecipePreferences from "../RecipePreferences";
import type {Recipe} from "../api/recipeTypes";
export default function RecipeTastePanel({familyId, recipe}:{familyId:string;recipe:Recipe}) {
  const {locale}=useI18n();const [open,setOpen]=useState(false);
  return <details className="nf-taste-panel" onToggle={event=>setOpen(event.currentTarget.open)}><summary>{locale === "pt-PT" ? "Quem gosta desta receita? · Avaliar por pessoa" : "Who likes this recipe? · Rate per person"}</summary>{open ? <RecipePreferences familyId={familyId} fixedRecipe={recipe}/> : null}</details>;
}
