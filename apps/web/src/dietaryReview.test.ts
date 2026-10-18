import { describe, expect, it, vi, afterEach } from "vitest";
import { reviewCounts } from "./RecipeDietaryReview";
import { listConditions, saveCondition, reviewSubstitution, type HealthCondition, type ReviewRecipe, type Substitution } from "./api/dietaryReviewClient";

afterEach(() => vi.unstubAllGlobals());
describe("dietary review boundaries", () => {
  it("keeps rejected alternatives out of open proposal counts without treating review as safety", () => {
    const rows = [{ingredients: [{substitutions: [{status: "proposed"}, {status: "reviewed"}, {status: "rejected"}]}]}, {ingredients: []}] as unknown as ReviewRecipe[];
    expect(reviewCounts(rows)).toEqual({recipes: 2, proposals: 2, missingIngredients: 1});
  });
  it("writes a condition only to its family/person and includes the expected version on revision", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ok: true, json: async () => ({id: "condition"})});
    vi.stubGlobal("fetch", fetchMock);
    const input = {code: "sibo", name: "SIBO", status: "reported", source: "user", source_reference: null, started_on: null, ended_on: null, notes: null} as const;
    await saveCondition("family", "person", input, {id: "condition", version: 3} as HealthCondition);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toContain("/api/families/family/persons/person/conditions/condition");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body)).toEqual({...input, expected_version: 3});
  });
  it("reports server conflicts instead of treating an unsaved review as complete", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ok: false, status: 409, json: async () => ({detail: "reload"})}));
    await expect(reviewSubstitution("family", {id: "p", version: 1} as Substitution, "reviewed", "notes")).rejects.toThrow("reload");
  });
  it("does not turn a failed condition lookup into an empty health history", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ok: false, status: 404, json: async () => ({detail: "not found"})}));
    await expect(listConditions("wrong-family", "person")).rejects.toThrow("not found");
  });
  it("sends complete replacement amounts and can explicitly clear an unknown amount", async()=>{
    const fetchMock=vi.fn().mockResolvedValue({ok:true,json:async()=>({version:2})});vi.stubGlobal("fetch",fetchMock);
    const row={id:"s",version:1} as Substitution;
    await reviewSubstitution("family",row,"proposed","Whole recipe",{replacement_quantity:"12.5",replacement_unit:"ml"});
    expect(JSON.parse(fetchMock.mock.calls[0]![1].body)).toEqual({expected_version:1,status:"proposed",notes:"Whole recipe",replacement_quantity:"12.5",replacement_unit:"ml"});
    await reviewSubstitution("family",row,"proposed","Unknown amount",{replacement_quantity:null,replacement_unit:null});
    expect(JSON.parse(fetchMock.mock.calls[1]![1].body).replacement_quantity).toBeNull();
    await reviewSubstitution("family",row,"reviewed","Notes only");
    expect(JSON.parse(fetchMock.mock.calls[2]![1].body)).not.toHaveProperty("replacement_quantity");
  });
});
