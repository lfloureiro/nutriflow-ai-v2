import { afterEach, describe, expect, it, vi } from "vitest";
import { nextWeekMonday, exclusionGroups, exclusionsForMeal } from "./PlanningJourney";
import { saveWeekSetup } from "./api/planningWorkspaceClient";
import { weeklyPlanRequest } from "./WeeklyProposalPreview";
import type { ReviewRecipe } from "./api/dietaryReviewClient";
import { shoppingIssueLabel, formatShoppingQuantity } from "./ShoppingListScreen";

afterEach(() => vi.unstubAllGlobals());
describe("guided week planning", () => {
  it("formats shopping amounts without storage zeros while retaining small quantities",()=>{
    expect(formatShoppingQuantity("1680.000000","en")).toBe("1,680");
    expect(formatShoppingQuantity("140.0000","pt-PT")).toBe("140");
    expect(formatShoppingQuantity("0.000001","pt-PT")).toBe("0,000001");
    expect(formatShoppingQuantity("","pt-PT")).toBe("");
  });
  it("starts the next calendar week on Monday across week and month boundaries", () => {
    expect(nextWeekMonday("2026-10-18")).toBe("2026-10-19");
    expect(nextWeekMonday("2026-10-19")).toBe("2026-10-26");
    expect(nextWeekMonday("2026-12-31")).toBe("2027-01-04");
  });
  it("uses explicit reference links and deduplicates ingredients shared by recipes", () => {
    const ref = {classification:"high",reference_key:"garlic",name_pt:"Alho",name_en:"Garlic"};
    const rows = [{ingredients:[{food_item_id:"f1", references:[ref]}]}, {ingredients:[{food_item_id:"f1",references:[ref]},{food_item_id:"f2",references:[]}]}] as unknown as ReviewRecipe[];
    expect(exclusionGroups(rows)).toEqual([{key:"garlic",namePt:"Alho",nameEn:"Garlic",ids:["f1"]}]);
  });
  it("saves the selected period and group without using diagnosis text as a restriction", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ok:true,json:async()=>({version:2})});vi.stubGlobal("fetch",fetchMock);
    await saveWeekSetup("family",{week_start:"2026-10-19",version:1,person_ids:["a","b"],meal_types:["dinner"],excluded_food_item_ids:["garlic"]});
    const [url,init]=fetchMock.mock.calls[0]!;
    expect(url).toContain("/planning-setup/2026-10-19");
    expect(JSON.parse(init.body)).toEqual({attendance:[],meal_sources:{},expected_version:1,person_ids:["a","b"],meal_types:["dinner"],excluded_food_item_ids:["garlic"]});
  });
  it("shows automatic adaptations only for the actual attendees and meal scope",()=>{
    const rules={excluded_food_item_ids:["onion"],warnings:[],sources:[{person_id:"p",source_id:"s",source_kind:"condition" as const,label:"SIBO",food_item_ids:["onion"],dates:["2026-10-20"],meal_types:["dinner"]}]};
    expect(exclusionsForMeal(["manual"],rules,"2026-10-20","dinner",["a","b"])).toEqual(["manual"]);
    expect(exclusionsForMeal([],rules,"2026-10-20","dinner",["p","b"])).toEqual(["onion"]);
    expect(exclusionsForMeal([],rules,"2026-10-20","lunch",["p","b"])).toEqual([]);
  });
  it("preserves per-meal attendance during saving and acceptance", async()=>{
    const attendance=[{planning_date:"2026-10-20",meal_type:"dinner" as const,person_ids:["a","c"]}];
    const fetchMock=vi.fn().mockResolvedValue({ok:true,json:async()=>({version:2})}); vi.stubGlobal("fetch",fetchMock);
    await saveWeekSetup("family",{week_start:"2026-10-19",version:1,person_ids:["a","b","c"],meal_types:["dinner"],excluded_food_item_ids:[],attendance});
    expect(JSON.parse(fetchMock.mock.calls[0]![1].body).attendance).toEqual(attendance);
    const slots=[{slot_key:"dinner",person_ids:["a","c"]}];
    expect(weeklyPlanRequest({person_ids:["a","b","c"],slots} as Parameters<typeof weeklyPlanRequest>[0],[]).slots).toEqual(slots);
  });
  it("preserves requested exclusions when converting a reviewed proposal to acceptance", () => {
    const request = {person_ids:["a","b"],excluded_food_item_ids:["f1"],slots:[]};
    expect(weeklyPlanRequest(request,[]).excluded_food_item_ids).toEqual(["f1"]);
  });
  it("explains estimated shopping quantities without leaking persistence identifiers", () => {
    expect(shoppingIssueLabel("Recipe 'Massa': shopping quantities use the same estimated serving count as meal planning; confirm yield before purchasing.",true)).toContain("Massa: quantidades aproximadas");
  });
});
