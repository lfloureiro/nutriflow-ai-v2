import {describe,it,expect} from "vitest";
import {parseRoute,routeHash,requestNavigation,registerNavigationBlocker} from "./navigation";
describe("bookmarkable navigation",()=>{
 it("round trips view, week, person and house context without family credentials",()=>{
  const route={view:"meals",mode:"week",date:"2026-11-19",person:"person-1",house:"pantry"} as const;
  expect(parseRoute(routeHash(route))).toEqual(route);expect(routeHash(route)).not.toContain("family");
 });
 it("rejects malformed dates, unknown screens and unsupported tabs/modes",()=>{
  expect(parseRoute("#/unknown?mode=other&tab=unsafe&date=2026-02-31&person=<script>")).toEqual({view:"home",mode:"today",house:"recipes"});
  expect(parseRoute("#/house?tab=ingredients&date=2026-11-19")).toMatchObject({view:"house",house:"ingredients",date:"2026-11-19"});
 });
 it("honours and releases edit blockers",()=>{
  const release=registerNavigationBlocker(()=>false);expect(requestNavigation()).toBe(false);release();expect(requestNavigation()).toBe(true);
 });
});
