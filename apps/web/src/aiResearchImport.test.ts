import { describe, expect, it } from "vitest";
import { buildAIResearchExport, previewAIResearchImport } from "./aiResearchImport";
import type { ReviewRecipe } from "./api/dietaryReviewClient";

const recipes = [{
  id: "recipe-1",
  name: "Arroz de bacalhau",
  ingredients: [{
    id: "ingredient-1",
    food_item_id: "food-onion",
    name: "Cebola",
    quantity: "100",
    unit: "g",
    substitutions: [{replacement_name:"Cebolinho",status:"proposed"}],
  }, {
    id: "ingredient-2",
    food_item_id: "food-garlic",
    name: "Alho",
    quantity: "10",
    unit: "g",
    substitutions: [],
  }],
}] as unknown as ReviewRecipe[];

function payload(overrides: Record<string, unknown> = {}) {
  return JSON.stringify({
    schema_version:"nutriflow.ai-review.v1",
    suggestions:[{
      recipe_id:"recipe-1",
      ingredient_id:"ingredient-2",
      replacement_name:"Azeite aromatizado com alho",
      evidence_url:"https://www.monashfodmap.com/example",
      notes:"Verificar porção e rótulo, sem aprovação clínica.",
      evidence_status:"unverified",
      ...overrides,
    }],
  });
}

describe("AI research schema", () => {
  it("exports only excluded family ingredients with stable IDs and an unverified example", () => {
    const json = JSON.parse(buildAIResearchExport(recipes, ["food-onion"])) as {
      ingredients:{ingredient_id:string}[];output_example:{suggestions:{evidence_status:string}[]};
    };
    expect(json.ingredients).toEqual([
      expect.objectContaining({ingredient_id:"ingredient-1"}),
    ]);
    expect(json.output_example.suggestions[0]?.evidence_status).toBe("unverified");
  });
  it("previews a legitimate sourced candidate without applying a mutation", () => {
    const preview = previewAIResearchImport(payload(), recipes);
    expect(preview).toHaveLength(1);
    expect(preview[0]?.ingredientName).toBe("Alho");
    expect(preview[0]?.issue).toBeUndefined();
  });
  it("rejects foreign identifiers, unsafe URLs and any status claiming approval", () => {
    expect(() => previewAIResearchImport(payload({ingredient_id:"foreign"}), recipes)).toThrow();
    expect(() => previewAIResearchImport(payload({recipe_id:"foreign"}), recipes)).toThrow();
    expect(() => previewAIResearchImport(payload({evidence_url:"http://example.com"}), recipes)).toThrow();
    expect(() => previewAIResearchImport(payload({evidence_url:"javascript:alert(1)"}), recipes)).toThrow();
    expect(() => previewAIResearchImport(payload({evidence_status:"approved"}), recipes)).toThrow();
    expect(() => previewAIResearchImport(payload({replacement_name:""}), recipes)).toThrow();
  });
  it("flags existing and repeated proposals instead of re-importing them", () => {
    const existing = previewAIResearchImport(payload({
      ingredient_id:"ingredient-1",replacement_name:"Cebolinho",
    }), recipes);
    expect(existing[0]?.issue).toMatch(/já registada/);
    const duplicates = JSON.parse(payload()) as {suggestions:unknown[]};
    duplicates.suggestions.push(duplicates.suggestions[0]);
    const preview = previewAIResearchImport(JSON.stringify(duplicates), recipes);
    expect(preview[1]?.issue).toMatch(/repetida/);
  });
  it("rejects unverified nutrition quantities unless quantity and unit are paired", () => {
    expect(() => previewAIResearchImport(payload({proposed_quantity:"20"}),recipes)).toThrow();
    expect(previewAIResearchImport(payload({proposed_quantity:"20",proposed_unit:"ml"}),recipes)[0]?.proposed_unit).toBe("ml");
  });
});
