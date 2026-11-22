export type IconName = "home" | "calendar" | "book" | "people" | "bag" | "leaf" | "arrow" | "settings" | "refresh" | "clock" | "spark" | "pantry" | "coffee" | "utensils" | "apple" | "cloche";
const paths: Record<IconName, string> = {
  home: "M3 11 12 3l9 8M5 9v12h14V9m-10 12v-7h6v7",
  calendar: "M4 5h16v16H4zM8 3v4m8-4v4M4 10h16m-11 4h2m3 0h2m-7 4h2",
  book: "M4 4h7q2 0 2 3v14q-2-3-5-3H4zm9 3q0-3 3-3h4v14h-4q-3 0-3 3",
  people: "M8 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8m8 0a3 3 0 1 0 0-6M2 21v-3q0-4 6-4t6 4v3m2-7q6 0 6 4v3",
  bag: "M5 8h14l-1 13H6zM9 8V6a3 3 0 0 1 6 0v2",
  leaf: "M5 18q-3-12 15-15 0 18-15 15m-2 4L17 7",
  arrow: "M4 12h16m-6-6 6 6-6 6",
  settings: "M9.5 3h5l.6 2.2 1.8 1 2.2-.6 2.5 4.3-1.6 1.6v2l1.6 1.6-2.5 4.3-2.2-.6-1.8 1-.6 2.2h-5l-.6-2.2-1.8-1-2.2.6-2.5-4.3 1.6-1.6v-2L2.5 9.9 5 5.6l2.2.6 1.8-1 .5-2.2ZM12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7",
  refresh: "M20 10a8 8 0 1 0 0 5m0-11v6h-6",
  clock: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18m0 5v5l3 2",
  spark: "m12 2 2.7 7.3L22 12l-7.3 2.7L12 22l-2.7-7.3L2 12l7.3-2.7z",
  pantry: "M4 3h16v18H4zM4 11h16M8 6v2m0 7v3",
  coffee: "M4 8h13v6a6.5 6.5 0 0 1-13 0zm13 1h2a3 3 0 0 1 0 6h-2M3 21h17M8 3c-2 2 2 2 0 4m5-4c-2 2 2 2 0 4",
  utensils: "M4 3v7m4-7v7m4-7v7M4 10h8m-4 0v11M18 3c-3 3-3 8 0 10h2V3h-2zm1 10v8",
  apple: "M12 7c-5-4-10 1-9 7 1 6 4 8 8 6l1-1 1 1c4 2 7 0 8-6 1-6-4-11-9-7zm0 0c0-3 2-5 5-5m-5 5c-1-3-3-4-5-4",
  cloche: "M3 18h18M5 18c0-7 3-11 7-11s7 4 7 11M10 5a2 2 0 0 1 4 0M2 21h20",
};
export default function Icon({name, className = ""}: {name: IconName; className?: string}) {
  return <svg className={`nf-icon ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]}/></svg>;
}
