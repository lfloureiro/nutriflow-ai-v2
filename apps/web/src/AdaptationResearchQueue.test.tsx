import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import AdaptationResearchQueue, { adaptationResearchItems, buildAdaptationResearchBrief } from "./AdaptationResearchQueue";
import type { ReviewRecipe } from "./api/dietaryReviewClient";
import { researchSuggestionsForIngredient } from "./adaptationResearchReferences";

vi.mock("./i18n", () => ({ useI18n: () => ({ locale: "pt-PT" }) }));

const recipes = [{
  id: "recipe-1",
  name: "Jantar da família",
  source: "family",
  assessment_status: "not_evaluated",
  ingredients: [
    { id: "ingredient-1", food_item_id: "excluded-onion", name: "Cebola", quantity: "100", unit: "g", references: [], substitutions: [] },
    { id: "ingredient-2", food_item_id: "excluded-milk", name: "Leite", quantity: "200", unit: "ml", references: [], substitutions: [
      { id: "proposal-1", recipe_ingredient_id: "ingredient-2", replacement_name: "Leite sem lactose", status: "proposed", notes: "", version: 1 },
    ] },
    { id: "ingredient-3", food_item_id: "allowed-potato", name: "Batata", quantity: "100", unit: "g", references: [], substitutions: [] },
  ],
}] as unknown as ReviewRecipe[];

describe("family adaptation research backlog", () => {
  it("groups repeated ingredient names into evidence-backed research hypotheses", () => {
    expect(researchSuggestionsForIngredient("Alho congelado")[0]?.replacement).toContain("Azeite");
    expect(researchSuggestionsForIngredient("Alho francês")[0]?.replacement.toLocaleLowerCase()).toContain("parte verde");
    expect(researchSuggestionsForIngredient("Cebola picada congelada")[0]?.replacement).toContain("Cebolinho");
    expect(researchSuggestionsForIngredient("Iogurte grego")[0]?.brand).toBe("Mevgal");
    expect(researchSuggestionsForIngredient("Massa cotovelos")[0]?.brand).toBe("Auchan");
    expect(researchSuggestionsForIngredient("Esparguete")[0]?.brand).toBe("Rummo");
    expect(researchSuggestionsForIngredient("Cogumelos congelados")[0]?.replacement).toContain("conserva");
    expect(researchSuggestionsForIngredient("Lata de feijão vermelho")[0]?.reason).toContain("NÃO equivale");
    expect(researchSuggestionsForIngredient("Cenouras")).toHaveLength(0);
  });

  it("finds unresolved excluded ingredients even without any substitution", () => {
    const items = adaptationResearchItems(recipes, ["excluded-onion", "excluded-milk"]);
    expect(items).toHaveLength(2);
    expect(items.find(item => item.ingredientName === "Cebola")?.missing).toBe(true);
    expect(items.find(item => item.ingredientName === "Leite")?.missing).toBe(false);
    expect(items.some(item => item.ingredientName === "Batata")).toBe(false);
  });

  it("retains a variant ingredient for person-specific validation without requesting new evidence", () => {
    const withVariant = [{
      ...recipes[0],
      active_variants: [{
        id: "v", recipe_id: "variant", name: "Jantar revisto",
        operations: [{ recipe_ingredient_id: "ingredient-1", replacement_name: "Cebolinho", quantity: "10", unit: "g", preparation: "" }],
      }],
    }] as ReviewRecipe[];
    const items = adaptationResearchItems(withVariant, ["excluded-onion", "excluded-milk"]);
    expect(items.map(item => item.ingredientName)).toEqual(["Cebola", "Leite"]);
    expect(items[0]?.hasVariant).toBe(true);
    expect(items[0]?.missing).toBe(false);
  });

  it("builds a sourced AI research brief without declaring any replacement safe", () => {
    const brief = buildAdaptationResearchBrief(adaptationResearchItems(recipes, ["excluded-onion"]));
    expect(brief).toContain("Monash University");
    expect(brief).toContain("Auchan");
    expect(brief).toContain("Cebola (100 g)");
    expect(brief).toContain("Não inventes valores nutricionais");
    expect(brief).not.toContain("Cebola é low FODMAP");
  });

  it("renders research links and explicitly states missing evidence", () => {
    const html = renderToStaticMarkup(
      <AdaptationResearchQueue recipes={recipes} excluded={["excluded-onion", "excluded-milk"]} familyId="family-1" onChanged={() => {}} />,
    );
    expect(html).toContain("Ingredientes para investigar");
    expect(html).toContain("Sem substituição");
    expect(html).toContain("Monash");
    expect(html).toContain("Auchan");
    expect(html).toContain("Continente");
    expect(html).toContain("não alteram refeições");
  });
});
