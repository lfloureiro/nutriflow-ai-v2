import { describe, expect, it } from "vitest";

import type { PersonEnergyProfile } from "./api/setupTypes";
import type { Person } from "./api/types";
import {
  energyProfileNeedsUpdate,
  type PersonProfileEditorValues,
} from "./PersonProfileEditor";

const person: Person = {
  id: "person-1",
  family_id: "family-1",
  first_name: "Ana",
  last_name: "Teste",
  birth_date: "1980-05-10",
  preferred_locale: "pt-PT",
  timezone: "Europe/Lisbon",
  created_at: "2026-08-24T10:00:00Z",
  updated_at: "2026-08-24T10:00:00Z",
};

const profile: PersonEnergyProfile = {
  person_id: person.id,
  sex_for_energy_calculation: "female",
  activity_level: "light",
  standard_breakfast_kcal: "320.00",
  height_cm: "165.0000",
  weight_kg: "68.0000",
  goal_type: "lose",
  target_rate_kg_per_week: "0.500",
  estimated_bmr_kcal: "1350.00",
  estimated_tdee_kcal: "1856.25",
  energy_min_kcal: "1306.25",
  energy_max_kcal: "1506.25",
  calculation_version: "mifflin-st-jeor-v1",
};

function values(patch: Partial<PersonProfileEditorValues> = {}): PersonProfileEditorValues {
  return {
    firstName: person.first_name,
    lastName: person.last_name ?? "",
    birthDate: person.birth_date ?? "",
    timezone: person.timezone,
    sex: profile.sex_for_energy_calculation,
    height: profile.height_cm,
    weight: profile.weight_kg,
    activity: profile.activity_level,
    goal: profile.goal_type,
    rate: profile.target_rate_kg_per_week ?? "",
    breakfast: profile.standard_breakfast_kcal,
    ...patch,
  };
}

describe("energy profile change detection", () => {
  it("does not version energy when only identity fields change", () => {
    expect(
      energyProfileNeedsUpdate(person, profile, values({ firstName: "Maria", lastName: "Nova" })),
    ).toBe(false);
  });

  it("treats equivalent decimal formatting as unchanged", () => {
    expect(
      energyProfileNeedsUpdate(
        person,
        profile,
        values({ height: "165", weight: "68,0", rate: "0,5", breakfast: "320" }),
      ),
    ).toBe(false);
  });

  it("versions energy when a calculation dependency changes", () => {
    expect(energyProfileNeedsUpdate(person, profile, values({ weight: "67.5" }))).toBe(true);
    expect(
      energyProfileNeedsUpdate(person, profile, values({ birthDate: "1981-05-10" })),
    ).toBe(true);
    expect(
      energyProfileNeedsUpdate(person, profile, values({ timezone: "Europe/Madrid" })),
    ).toBe(true);
  });

  it("allows identity-only editing before an energy profile exists", () => {
    expect(
      energyProfileNeedsUpdate(person, null, {
        firstName: "Maria",
        lastName: "Nova",
        birthDate: person.birth_date ?? "",
        timezone: person.timezone,
        sex: "",
        height: "",
        weight: "",
        activity: "",
        goal: "maintain",
        rate: "",
        breakfast: "",
      }),
    ).toBe(false);
  });
});
