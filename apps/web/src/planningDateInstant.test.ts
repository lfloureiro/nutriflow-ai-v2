import { describe, expect, it } from "vitest";
import { planningDateInstant } from "./planningDateInstant";

describe("planning-day instant",()=>{
  it("uses Lisbon winter offset and same local calendar date",()=>{
    expect(planningDateInstant("2026-11-20","Europe/Lisbon")).toBe("2026-11-20T12:00:00+00:00");
  });
  it("uses Lisbon summer offset including daylight saving time",()=>{
    expect(planningDateInstant("2026-07-20","Europe/Lisbon")).toBe("2026-07-20T12:00:00+01:00");
  });
  it("supports half-hour timezones",()=>{
    expect(planningDateInstant("2026-11-20","Asia/Kolkata")).toBe("2026-11-20T12:00:00+05:30");
  });
  it("does not mistake a different UTC calendar day for the intended local day",()=>{
    expect(planningDateInstant("2026-11-20","Pacific/Auckland")).toBe("2026-11-20T12:00:00+13:00");
  });
});
