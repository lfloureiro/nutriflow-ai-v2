import {describe, expect, it} from "vitest";
import {retailEvidenceLabel} from "./RetailAlternativeCards";
describe("retail label coverage",()=>{
  it("does not imply nutrition coverage from an ingredient list",()=>{
    expect(retailEvidenceLabel("retailer_ingredients_only",true)).toContain("nutrição por confirmar");
    expect(retailEvidenceLabel("retailer_ingredients_only",false)).toContain("nutrition unconfirmed");
    expect(retailEvidenceLabel("retailer_description_only",true)).toContain("Rótulo completo");
    expect(retailEvidenceLabel("unknown",false)).toContain("Full label unconfirmed");
  });
});
