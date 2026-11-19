import {afterEach,describe,expect,it,vi} from "vitest";
import {variantDraftIssues} from "./RecipeVariantEditor";
import {createRecipeVariant,activateRecipeVariant,type RecipeVariant} from "./api/recipeVariantClient";

afterEach(()=>vi.unstubAllGlobals());
describe("complete recipe variant workflow",()=>{
  it("requires explicit products, quantities, preparation and confirmed servings",()=>{
    const operation={recipe_ingredient_id:"onion",replacement_food_item_id:"chives",quantity:"10",unit:"g",preparation:"Only green tops"};
    expect(variantDraftIssues("2",[operation])).toEqual([]);
    expect(variantDraftIssues("",[operation])).toContain("servings");
    expect(variantDraftIssues("2",[])).toContain("operations");
    expect(variantDraftIssues("2",[{...operation,replacement_food_item_id:""}])).toContain("onion");
    expect(variantDraftIssues("2",[{...operation,quantity:"0"}])).toContain("onion");
    expect(variantDraftIssues("2",[{...operation,preparation:" "}])).toContain("onion");
  });
  it("saves a complete independent draft without issuing an activation",async()=>{
    const fetchMock=vi.fn().mockResolvedValue({ok:true,json:async()=>({status:"draft"})});vi.stubGlobal("fetch",fetchMock);
    const input={base_recipe_id:"base",name:"Rice and chives",serving_count:"2",operations:[{recipe_ingredient_id:"onion",replacement_food_item_id:"chives",quantity:"10",unit:"g",preparation:"Fresh"}]};
    await createRecipeVariant("family",input);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]![0]).toContain("/families/family/recipe-variants");
    expect(JSON.parse(fetchMock.mock.calls[0]![1].body)).toEqual(input);
  });
  it("does not report a conflicting activation as successful",async()=>{
    vi.stubGlobal("fetch",vi.fn().mockResolvedValue({ok:false,status:409,json:async()=>({detail:"Variant changed; reload"})}));
    await expect(activateRecipeVariant("family",{id:"v"} as RecipeVariant,{expected_version:1,planning_date:"2030-01-07",meal_type:"dinner",participants:[{person_id:"p",quantity:"1"}]})).rejects.toThrow("Variant changed");
  });
});
