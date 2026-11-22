import { describe, expect, it } from "vitest";
import { attendeeRestrictionSummary, personMealPortion, selectedMealRestrictions } from "./SelectedMealOptions";
import type { PlanningRestrictions } from "./api/planningWorkspaceClient";
import type { SelectedMealContext } from "./SelectedMealOptions";

const rules: PlanningRestrictions = {
  excluded_food_item_ids: ["not-authoritative-here"],
  warnings: ["Evidence needs review"],
  sources: [
    {
      person_id: "one",
      source_id: "allergy-1",
      source_kind: "condition",
      label: "Recorded allergy",
      food_item_ids: ["food-a"],
      dates: ["2026-11-19"],
      meal_types: ["dinner"],
    },
    {
      person_id: "two",
      source_id: "diet-1",
      source_kind: "diet",
      label: "Dietary exclusion",
      food_item_ids: ["food-b"],
      dates: ["2026-11-19"],
      meal_types: ["dinner"],
    },
    {
      person_id: "one",
      source_id: "other-day",
      source_kind: "condition",
      label: "Different date",
      food_item_ids: ["food-c"],
      dates: ["2026-11-20"],
      meal_types: ["dinner"],
    },
    {
      person_id: "absent",
      source_id: "not-attending",
      source_kind: "condition",
      label: "Absent person",
      food_item_ids: ["food-d"],
      dates: ["2026-11-19"],
      meal_types: ["dinner"],
    },
  ],
};
const context: SelectedMealContext = {
  recipeId: null,
  planningDate: "2026-11-19",
  mealType: "dinner",
  personIds: ["one", "two", "three"],
  appliedChanges: [],
};

describe("per-person restrictions displayed in a meal drawer", () => {
  it("keeps evidence for each attending person separately and preserves unknown coverage", () => {
    const selected = selectedMealRestrictions(rules, context);
    const summary = attendeeRestrictionSummary(selected, context.personIds);
    expect(summary.map(item => item.personId)).toEqual(["one", "two", "three"]);
    expect(summary.map(item => item.sources.map(source => source.source_id)))
      .toEqual([["allergy-1"], ["diet-1"], []]);
    expect(selected.excluded_food_item_ids).toEqual(["food-a", "food-b"]);
    expect(selected.warnings).toEqual(["Evidence needs review"]);
  });

  it("does not leak restrictions from absent people, other dates or meal slots", () => {
    const selected = selectedMealRestrictions(rules, {
      ...context,
      personIds: ["one"],
      mealType: "lunch",
    });
    expect(selected.sources).toEqual([]);
    expect(attendeeRestrictionSummary(selected, ["one"])[0]?.sources).toEqual([]);
    expect(selected.excluded_food_item_ids).toEqual([]);
  });
});

describe("per-person meal portion provenance",()=>{
  it("preserves exact planned quantities and units without converting or fabricating energy",()=>{
    const proposal={...context,portions:[
      {person_id:"one",quantity:"3.0000",unit:"emb"},
      {person_id:"two",quantity:"1",unit:"serving"},
    ]};
    expect(personMealPortion(proposal,"one")).toEqual({quantity:"3.0000",unit:"emb",recorded:false});
    expect(personMealPortion(proposal,"two")).toEqual({quantity:"1",unit:"serving",recorded:false});
    expect(personMealPortion(proposal,"three")).toBeNull();
  });
  it("leaves missing quantities unknown and does not assume people are present",()=>{
    const proposal={...context,portions:[{person_id:"one",quantity:"",unit:"g"}]};
    expect(personMealPortion(proposal,"one")).toBeNull();
    expect(personMealPortion({...context,portions:undefined},"one")).toBeNull();
  });
});
