import {parseAvatarPreference} from "./ui/avatarPreferences";
import {describe, expect, it, vi} from "vitest";
import {renderToStaticMarkup} from "react-dom/server";
import FamilyHome, {currentMealKind, nextFamilyMeal} from "./FamilyHome";
import PersonAvatar, {avatarAgeGroup, familySkinPalette, avatarInitials, avatarTone} from "./ui/PersonAvatar";
import Brand, { APP_VERSION } from "./ui/Brand";
import type {FamilyDashboard, FamilyDashboardMeal} from "./api/types";

vi.mock("./i18n",()=>({useI18n:()=>({locale:"pt-PT", t:(key:string)=>key})}));
const meal=(id:string, scheduled_at:string, status="planned"):FamilyDashboardMeal=>({id,scheduled_at,status,meal_type:"dinner",title:"Jantar de teste",timezone:"Europe/Lisbon",location:"Casa",participant_person_ids:["person-test"]});
const dashboard:FamilyDashboard={family_id:"synthetic-family",family_name:"Família de teste",timezone:"Europe/Lisbon",dashboard_date:"2026-11-18",members:[{person_id:"person-test",first_name:"Ana",last_name:"Silva",timezone:"Europe/Lisbon",health:null,nutrition:null}],meals:[]};
describe("UX foundation with authoritative dashboard data",()=>{
  it("displays the frontend semantic version alongside Casa à Mesa",()=>{
    expect(APP_VERSION).toMatch(/^\d+\.\d+\.\d+$/);
    const html=renderToStaticMarkup(<Brand/>);
    expect(html).toContain("Casa à Mesa");
    expect(html).toContain(`v${APP_VERSION}`);
    expect(html).toContain(`Versão ${APP_VERSION}`);
  });

  it("keeps a stable avatar tone across name changes without exposing identity keys",()=>{
    expect(avatarTone("person-test")).toBe(avatarTone("person-test"));
    const html=renderToStaticMarkup(<PersonAvatar identity="private-person-id" name="Ana Silva"/>);
    expect(html).toContain('aria-label="Ana Silva"');expect(html).toContain("AS");expect(html).not.toContain("private-person-id");
  });
  it("uses age boundaries and a common family skin palette with neutral missing data",()=>{
    expect([null,-1,12,13,17,18,29,30,44,45,64,65].map(age=>avatarAgeGroup(age))).toEqual(["unknown","unknown","child","teen","teen","young","young","adult","adult","mature","mature","senior"]);
    const render=(identity:string,sex?:"male"|"female")=>renderToStaticMarkup(<PersonAvatar identity={identity} familyIdentity="family-1" name="Test" age={10} sex={sex}/>);
    expect(render("a","female")).toContain(familySkinPalette("family-1"));expect(render("b","male")).toContain(familySkinPalette("family-1"));expect(render("c")).toContain('data-hair="neutral"');expect(render("a","female")).toContain('data-age-group="child"');
  });
  it("distinguishes adult generations and all six styles without changing shared skin",()=>{
    const render=(age:number,variant:number)=>renderToStaticMarkup(<PersonAvatar identity="same" familyIdentity="family" name="Test" sex="male" age={age} preview={{variant}}/>);
    expect(render(23,0)).not.toBe(render(53,0));expect(render(53,0)).toContain('data-age-group="mature"');
    expect(new Set([0,1,2,3,4,5].map(variant=>render(23,variant))).size).toBe(6);
    expect(parseAvatarPreference('{"stage":"mature","style":"female","variant":4}')).toEqual({stage:"mature",style:"female",variant:4});
    expect(parseAvatarPreference('{"stage":"fake","style":"fake","variant":99}')).toEqual({});expect(parseAvatarPreference('broken')).toEqual({});
  });
  it("handles empty, accented and single-word names",()=>{
    expect(avatarInitials("  Inês  Maria Silva ")).toBe("IM");expect(avatarInitials("Luís")).toBe("L");expect(avatarInitials(" ")).toBe("");
  });
  it("chooses the next valid pending meal and never mutates API order",()=>{
    const meals=[meal("late","2026-11-18T20:00:00Z"),meal("cancelled","2026-11-18T14:00:00Z","cancelled"),meal("early","2026-11-18T18:00:00Z"),meal("invalid","invalid")];
    expect(nextFamilyMeal(meals,Date.parse("2026-11-18T17:00:00Z"))?.id).toBe("early");expect(meals[0]?.id).toBe("late");
    expect(nextFamilyMeal([meal("done","2026-11-18T18:00:00Z","completed")])).toBeUndefined();
  });
  it("focuses dinner near 21h instead of reviving an expired snack",()=>{
    const now=Date.parse("2026-11-18T20:55:00Z");
    const snack={...meal("snack","2026-11-18T16:00:00Z"),meal_type:"snack"};
    const dinner=meal("dinner","2026-11-18T20:00:00Z");
    expect(currentMealKind(now,"Europe/Lisbon")).toBe("dinner");
    expect(nextFamilyMeal([snack,dinner],now,"Europe/Lisbon")?.id).toBe("dinner");
    expect(nextFamilyMeal([snack],now,"Europe/Lisbon")).toBeUndefined();
    expect(nextFamilyMeal([{...dinner,status:"completed"},snack],now,"Europe/Lisbon")).toBeUndefined();
    expect(nextFamilyMeal([meal("yesterday","2026-11-17T20:00:00Z")],now,"Europe/Lisbon")).toBeUndefined();
  });
  it("uses the family timezone including summer time and meal boundaries",()=>{
    expect(currentMealKind(Date.parse("2026-07-18T17:30:00Z"),"Europe/Lisbon")).toBe("dinner");
    expect(currentMealKind(Date.parse("2026-11-18T20:55:00Z"),"America/New_York")).toBe("snack");
    for(const [hour,kind] of [[10,"breakfast"],[11,"lunch"],[14,"lunch"],[15,"snack"],[17,"snack"],[18,"dinner"]] as const)expect(currentMealKind(Date.parse(`2026-11-18T${hour}:00:00Z`),"Europe/Lisbon")).toBe(kind);
  });
  it("renders all four empty meal slots without inventing dishes or nutrition",()=>{
    const html=renderToStaticMarkup(<FamilyHome dashboard={dashboard} onPlanMeal={()=>{}} onOpenPerson={()=>{}}/>);
    for(const label of ["Pequeno-almoço","Almoço","Lanche","Jantar"])expect(html).toContain(label);
    expect(html.match(/nf-day-slot nf-day-slot-empty/g)).toHaveLength(4);
    expect(html).not.toContain("kcal");expect(html).not.toContain("Adequado");expect(html).toContain("Ana Silva");
  });
  it("keeps multiple events visible as a count rather than pretending a slot has one meal",()=>{
    const html=renderToStaticMarkup(<FamilyHome dashboard={{...dashboard,meals:[meal("one","2026-11-18T18:00:00Z"),meal("two","2026-11-18T19:00:00Z")]}} onPlanMeal={()=>{}} onOpenPerson={()=>{}}/>);
    expect(html).toContain("+1 refeições");expect(html).toContain("Jantar de teste");
  });
  it("keeps the product name ahead of the subtitle",()=>{
    const html=renderToStaticMarkup(<Brand/>);expect(html.indexOf("NutriFlow AI")).toBeLessThan(html.indexOf("Casa à Mesa"));
  });
});
