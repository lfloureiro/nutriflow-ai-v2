import { describe, expect, it } from "vitest";
import type { HealthCondition } from "./api/dietaryReviewClient";
import { conditionEvidenceSummary } from "./conditionEvidence";

const example: Pick<HealthCondition, "source" | "source_reference" | "started_on" | "ended_on" | "status"> = {
  source:"user", source_reference:null, started_on:null, ended_on:null, status:"reported",
};

describe("recorded condition evidence", () => {
  it("does not mistake missing dates or references for clinical evidence", () => {
    expect(conditionEvidenceSummary(example)).toEqual({
      hasSourceReference:false, hasStartDate:false, hasEndDate:false,
      needsProfessionalEvidence:false, hasIncompleteTimeline:true,
    });
  });
  it("flags a self-reported professional confirmation that cannot be verified", () => {
    const flags=conditionEvidenceSummary({...example,status:"confirmed"});
    expect(flags.needsProfessionalEvidence).toBe(true);
    expect(flags.hasIncompleteTimeline).toBe(true);
  });
  it("reports supplied provenance and dates without asserting medical validity", () => {
    const flags=conditionEvidenceSummary({
      ...example,source:"doctor",source_reference:"Profissional QA",
      started_on:"2026-10-01", ended_on:"2026-11-01",status:"confirmed",
    });
    expect(flags).toEqual({
      hasSourceReference:true, hasStartDate:true, hasEndDate:true,
      needsProfessionalEvidence:false, hasIncompleteTimeline:false,
    });
  });
  it("does not treat a claimed professional source without a reference as verified", () => {
    expect(conditionEvidenceSummary({...example,source:"doctor",status:"confirmed"}).needsProfessionalEvidence).toBe(true);
  });
});
