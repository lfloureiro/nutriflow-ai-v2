import { describe, expect, it } from "vitest";
import { normalizeMealImageName, resolveMealHeroImage } from "./mealHeroImages";

describe("next-meal image follows the same planned meal or proposal", () => {
  it("uses explicit meal image before a catalog match", () => {
    const result = resolveMealHeroImage({
      planned: {recipe_name:"Frango rápido · família", image_url:"https://cdn.example.org/frango.jpg"},
      proposal: {candidate_name:"Salmão no forno com ervas"},
    });
    expect(result?.kind).toBe("meal");
    expect(result?.src).toBe("https://cdn.example.org/frango.jpg");
  });
  it("uses an explicitly attached proposal image if there is no planned meal", () => {
    const result = resolveMealHeroImage({
      proposal:{candidate_name:"Salmão no forno com ervas",image_url:"https://cdn.example.org/proposal.jpg"},
    });
    expect(result?.kind).toBe("proposal");
    expect(result?.src).toContain("proposal.jpg");
  });
  it("normalizes the family suffix but never guesses from generic food words", () => {
    expect(normalizeMealImageName("Frango rápido · família")).toBe("frango rapido");
    expect(normalizeMealImageName("Escalopes ao vinho Madeira - família")).toBe("escalopes ao vinho madeira");
    expect(resolveMealHeroImage({planned:{title:"Frango rápido · família"}})?.src).toContain("Roasted_chicken".replace(/_/g,"%20").slice(0,7));
    expect(resolveMealHeroImage({planned:{title:"Escalopes ao vinho Madeira · família"}})).toBeNull();
    expect(resolveMealHeroImage({planned:{title:"Bifanas com natas"}})).toBeNull();
  });
  it("maps existing salmon, banana, cheese and tomato dishes by exact culinary name", () => {
    for(const title of [
      "Salmão no forno com ervinhas da provença",
      "Banana e frutos secos",
      "Torrada com queijo",
      "Pão, queijo e tomate",
      "Torrada mista",
      "Omelete de espinafres",
    ]) {
      const photo=resolveMealHeroImage({planned:{recipe_name:title}});
      expect(photo?.kind).toBe("catalog");
      expect(photo?.source).toContain("commons.wikimedia.org");
      expect(photo?.license).toBeTruthy();
      expect(photo?.author).toBeTruthy();
    }
  });
  it("never substitutes a planned meal's photo with a proposal's photo", () => {
    expect(resolveMealHeroImage({
      planned:{recipe_name:"Bifanas com natas"},
      proposal:{candidate_name:"Torrada com queijo",image_url:"https://cdn.example.org/toast.jpg"},
    })).toBeNull();
  });
  it("rejects unsafe URLs for optional API-supplied media", () => {
    expect(resolveMealHeroImage({planned:{title:"Receita privada",image_url:"javascript:alert(1)"}})).toBeNull();
    expect(resolveMealHeroImage({planned:{title:"Receita privada",image_url:"//malicious.example/x.jpg"}})).toBeNull();
    expect(resolveMealHeroImage({planned:{title:"Receita privada",image_url:"/images/saved.jpg"}})?.src).toBe("/images/saved.jpg");
  });
  it("has no image when neither plan nor eligible proposal is chosen", () => {
    expect(resolveMealHeroImage({})).toBeNull();
  });
});
