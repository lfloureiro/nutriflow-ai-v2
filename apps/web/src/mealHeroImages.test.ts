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
    expect(resolveMealHeroImage({planned:{title:"Frango rápido · família"}})?.src).toBe("/images/generated/frango-rapido.webp");
    expect(resolveMealHeroImage({planned:{title:"Escalopes ao vinho Madeira · família"}})?.alt).toContain("Madeira");
    expect(resolveMealHeroImage({planned:{title:"Bifanas com natas"}})?.kind).toBe("generated");
  });
  it("maps known generated recipe media by exact title, labeled as illustrative and with safe fallback", () => {
    for(const title of [
      "Salmão no forno com ervinhas da provença", "Banana e frutos secos",
      "Torrada mista", "Escalopes ao vinho Madeira · família",
      "Bifanas com natas", "Frango rápido · família",
    ]) {
      const photo=resolveMealHeroImage({planned:{recipe_name:title}});
      expect(photo?.kind).toBe("generated");
      expect(photo?.src).toMatch(/^\/images\/generated\/[a-z0-9-]+\.webp$/);
      expect(photo?.author).toContain("IA");
      expect(photo?.fallbackSrc).toBeTruthy();
      expect(photo?.source).toBeNull();
    }
    const original=resolveMealHeroImage({planned:{title:"Omelete de espinafres"}});
    expect(original?.kind).toBe("catalog");
    expect(original?.source).toContain("commons.wikimedia.org");
  });
  it("never substitutes a planned meal's photo with an unrelated proposal image", () => {
    expect(resolveMealHeroImage({
      planned:{recipe_name:"Bifanas com natas"},
      proposal:{candidate_name:"Torrada com queijo",image_url:"https://cdn.example.org/toast.jpg"},
    })?.src).toBe("/images/generated/bifanas-com-natas.webp");
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
