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
 it("round-trips an individual weekly meal without putting any family identifier in the URL",()=>{
  const route={view:"meals",mode:"week",date:"2026-11-19",meal:"dinner",house:"recipes"} as const;
  expect(routeHash(route)).toBe("#/meals?date=2026-11-19&meal=dinner&mode=week");
  expect(parseRoute(routeHash(route))).toEqual(route);
 });
 it("ignores invalid meal slots and does not expose drawer context outside a dated week",()=>{
  expect(parseRoute("#/meals?date=2026-11-19&mode=week&meal=other")).not.toHaveProperty("meal");
  expect(parseRoute("#/meals?mode=week&meal=dinner")).not.toHaveProperty("meal");
  expect(parseRoute("#/meals?date=2026-11-19&mode=today&meal=dinner")).not.toHaveProperty("meal");
  expect(parseRoute("#/shopping?date=2026-11-19&mode=week&meal=dinner")).not.toHaveProperty("meal");
 });
 it("prevents local tab transitions while any registered form has unsaved changes",()=>{
  const clean=registerNavigationBlocker(()=>true);
  const dirty=registerNavigationBlocker(()=>false);
  expect(requestNavigation()).toBe(false);
  dirty();
  expect(requestNavigation()).toBe(true);
  clean();
 });
 it("honours and releases edit blockers",()=>{
  const release=registerNavigationBlocker(()=>false);expect(requestNavigation()).toBe(false);release();expect(requestNavigation()).toBe(true);
 });
});
