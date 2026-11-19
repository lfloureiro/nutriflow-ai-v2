import {useEffect,useState} from "react";
export type AppView="home"|"meals"|"shopping"|"people"|"house"|"more";
export type HouseView="recipes"|"ingredients"|"pantry"|"substitutions"|"shopping"|"preferences"|"sources"|"restaurants"|"delivery";
export type AppRoute={view:AppView;mode:"today"|"week"|"prepare"|"recommend";date?:string;person?:string;house:HouseView};
const views=["home","meals","shopping","people","house","more"];
const houses=["recipes","ingredients","pantry","substitutions","shopping","preferences","sources","restaurants","delivery"];
export function parseRoute(hash:string):AppRoute {
 const [path,query]=hash.replace(/^#\/?/,"").split("?");const params=new URLSearchParams(query);
 const date=params.get("date")??"";const validDate=/^\d{4}-\d{2}-\d{2}$/.test(date)&&!Number.isNaN(Date.parse(date))&&new Date(date).toISOString().slice(0,10)===date;
 const mode=params.get("mode")??"today";const house=params.get("tab")??"recipes";const person=params.get("person")??"";
 return {view:(views.includes(path??"")?path:"home") as AppView,mode:(["today","week","prepare","recommend"].includes(mode)?mode:"today") as AppRoute["mode"],house:(houses.includes(house)?house:"recipes") as HouseView,...(validDate?{date}:{}),...(/^[a-zA-Z0-9-]{1,80}$/.test(person)?{person}:{})};
}
export function routeHash(route:AppRoute):string {
 const params=new URLSearchParams();if(route.date)params.set("date",route.date);if(route.mode!=="today")params.set("mode",route.mode);if(route.person)params.set("person",route.person);if(route.house!=="recipes")params.set("tab",route.house);
 return `#/${route.view}${params.size?`?${params}`:""}`;
}
const blockers=new Set<()=>boolean>();
export function registerNavigationBlocker(blocker:()=>boolean){blockers.add(blocker);return ()=>{blockers.delete(blocker);};}
export function requestNavigation():boolean {return [...blockers].every(check=>check());}
export function useAppRoute(){
 const [route,setRoute]=useState(()=>parseRoute(window.location.hash));
 useEffect(()=>{
  let previous=window.location.hash;
  const restore=()=>{const next=window.location.hash;if(next===previous)return;if(!requestNavigation()){window.history.pushState(null,"",previous||"#/home");return;}previous=next;setRoute(parseRoute(next));};
  window.addEventListener("popstate",restore);window.addEventListener("hashchange",restore);
  const sync=()=>{previous=window.location.hash;setRoute(parseRoute(previous));};window.addEventListener("nf-route",sync);
  return()=>{window.removeEventListener("popstate",restore);window.removeEventListener("hashchange",restore);window.removeEventListener("nf-route",sync);};
 },[]);
 function navigate(patch:Partial<AppRoute>,replace=false):boolean {
  const next={...parseRoute(window.location.hash),...patch};const hash=routeHash(next);if(!requestNavigation())return false;if(hash===window.location.hash)return true;
  window.history[replace?"replaceState":"pushState"](null,"",hash);setRoute(next);window.dispatchEvent(new Event("nf-route"));return true;
 }
 return {route,navigate};
}
