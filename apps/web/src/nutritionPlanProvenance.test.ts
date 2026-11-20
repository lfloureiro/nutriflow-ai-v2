import { describe, expect, it } from "vitest";
import type { NutritionPlanSummary } from "./api/planFitTypes";
import { nutritionPlanProvenance } from "./nutritionPlanProvenance";

const plan={
  id:"qa",person_id:"person-qa",lineage_id:"lineage-qa",version:2,
  supersedes_plan_id:null,title:"Plano sintético",source_type:"nutritionist",
  source_name:null,source_reference:null,original_text:null,status:"active",
  valid_from:"2026-11-01",valid_until:null,created_at:"2026-11-01",updated_at:"2026-11-01",
} as NutritionPlanSummary;

describe("nutrition plan provenance",()=>{
  it("keeps the absence of a professional reference explicit",()=>{
    expect(nutritionPlanProvenance(plan)).toEqual({
      declaredSource:null,sourceType:"nutritionist",reference:null,
      version:2,openEnded:true,professionalVerification:"not_verified_in_app",
    });
  });
  it("shows reported reference and bounded validity without certifying it",()=>{
    expect(nutritionPlanProvenance({
      ...plan,source_name:"Nutricionista QA",source_reference:"  Documento de teste  ",
      valid_until:"2027-01-01",
    })).toEqual({
      declaredSource:"Nutricionista QA",sourceType:"nutritionist",
      reference:"Documento de teste",version:2,openEnded:false,
      professionalVerification:"not_verified_in_app",
    });
  });
});
