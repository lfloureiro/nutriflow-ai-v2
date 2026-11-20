/** Represent noon on a selected calendar day in the person's time zone.
 * A UTC "now" request can silently evaluate a different calendar day.
 * Fixed local noon avoids DST rollover instants around midnight.
 */
export function planningDateInstant(day: string, timeZone: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) throw new Error("Invalid planning day");
  const probe = new Date(`${day}T12:00:00Z`);
  if (Number.isNaN(probe.valueOf())) throw new Error("Invalid planning day");
  const part = new Intl.DateTimeFormat("en-US", {
    timeZone, timeZoneName: "shortOffset", hour: "2-digit",
  }).formatToParts(probe).find((item) => item.type === "timeZoneName")?.value;
  const match = /^(?:GMT|UTC)(?:([+-])(\d{1,2})(?::(\d{2}))?)?$/.exec(part ?? "");
  if (!match) throw new Error("Unsupported timezone offset");
  const minutes = (Number(match[2] ?? "0") * 60 + Number(match[3] ?? "0")) * (match[1] === "-" ? -1 : 1);
  const sign = minutes < 0 ? "-" : "+";
  const hours = String(Math.floor(Math.abs(minutes) / 60)).padStart(2, "0");
  const mins = String(Math.abs(minutes) % 60).padStart(2, "0");
  return `${day}T12:00:00${sign}${hours}:${mins}`;
}
