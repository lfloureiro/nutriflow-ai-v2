import { useMemo, useState, type FormEvent } from "react";

import { ApiError } from "./api/client";
import { updatePerson } from "./api/setupClient";
import type {
  ActivityLevel,
  EnergyCalculationSex,
  NutritionGoalType,
  PersonEnergyProfile,
  PersonEnergyProfileCreate,
} from "./api/setupTypes";
import type { Person } from "./api/types";
import { useI18n } from "./i18n";
import { supportedTimezones } from "./timezones";

const COPY = {
  "pt-PT": {
    firstName: "Nome",
    lastName: "Apelido",
    birthDate: "Data de nascimento",
    timezone: "Fuso horário",
    energy: "Necessidades energéticas",
    energyHelp: "Peso, altura, objetivo e meta calórica só criam uma nova versão quando algum destes dados, a data de nascimento ou o fuso horário muda. O histórico anterior é preservado.",
    sex: "Sexo para cálculo energético",
    male: "Masculino",
    female: "Feminino",
    height: "Altura (cm)",
    weight: "Peso (kg)",
    activity: "Atividade habitual",
    sedentary: "Sedentário",
    light: "Ligeira",
    moderate: "Moderada",
    active: "Ativo",
    very_active: "Muito ativo",
    goal: "Objetivo",
    maintain: "Manter peso",
    lose: "Perder peso",
    gain: "Ganhar peso",
    rate: "Ritmo (kg/semana)",
    breakfast: "Pequeno-almoço padrão (kcal)",
    save: "Guardar perfil",
    saving: "A guardar…",
    cancel: "Cancelar",
    requiredName: "Indica o nome.",
    requiredBirth: "Indica a data de nascimento para calcular necessidades energéticas.",
    incompleteEnergy: "Para atualizar a meta calórica preenche sexo, altura, peso, atividade e pequeno-almoço padrão.",
    rateRequired: "Indica um ritmo semanal para perder ou ganhar peso.",
    invalidNumbers: "Altura, peso, pequeno-almoço e ritmo têm de ter valores válidos.",
    error: "Não foi possível guardar o perfil",
  },
  en: {
    firstName: "First name",
    lastName: "Last name",
    birthDate: "Date of birth",
    timezone: "Timezone",
    energy: "Energy needs",
    energyHelp: "Weight, height, goal and calorie target only create a new version when one of those inputs, date of birth or timezone changes. Prior history is preserved.",
    sex: "Sex for energy calculation",
    male: "Male",
    female: "Female",
    height: "Height (cm)",
    weight: "Weight (kg)",
    activity: "Usual activity",
    sedentary: "Sedentary",
    light: "Light",
    moderate: "Moderate",
    active: "Active",
    very_active: "Very active",
    goal: "Goal",
    maintain: "Maintain weight",
    lose: "Lose weight",
    gain: "Gain weight",
    rate: "Rate (kg/week)",
    breakfast: "Standard breakfast (kcal)",
    save: "Save profile",
    saving: "Saving…",
    cancel: "Cancel",
    requiredName: "Enter a first name.",
    requiredBirth: "Enter a date of birth to calculate energy needs.",
    incompleteEnergy: "To update the calorie target, enter sex, height, weight, activity and standard breakfast.",
    rateRequired: "Enter a weekly rate for weight loss or gain.",
    invalidNumbers: "Height, weight, breakfast and rate must contain valid values.",
    error: "The profile could not be saved",
  },
} as const;

export type PersonProfileEditorValues = {
  firstName: string;
  lastName: string;
  birthDate: string;
  timezone: string;
  sex: "" | EnergyCalculationSex;
  height: string;
  weight: string;
  activity: "" | ActivityLevel;
  goal: NutritionGoalType;
  rate: string;
  breakfast: string;
};

function initialValues(
  person: Person,
  profile: PersonEnergyProfile | null,
): PersonProfileEditorValues {
  return {
    firstName: person.first_name,
    lastName: person.last_name ?? "",
    birthDate: person.birth_date ?? "",
    timezone: person.timezone,
    sex: profile?.sex_for_energy_calculation ?? "",
    height: profile?.height_cm ?? "",
    weight: profile?.weight_kg ?? "",
    activity: profile?.activity_level ?? "",
    goal: profile?.goal_type ?? "maintain",
    rate: profile?.target_rate_kg_per_week ?? "",
    breakfast: profile?.standard_breakfast_kcal ?? "",
  };
}

function normalizedDecimal(value: string): string {
  return value.trim().replace(",", ".");
}

function sameDecimal(left: string, right: string): boolean {
  const leftNumber = Number(normalizedDecimal(left));
  const rightNumber = Number(normalizedDecimal(right));
  return Number.isFinite(leftNumber) && Number.isFinite(rightNumber) && leftNumber === rightNumber;
}

function positive(value: string): boolean {
  const numeric = Number(normalizedDecimal(value));
  return Number.isFinite(numeric) && numeric > 0;
}

function nonNegative(value: string): boolean {
  const numeric = Number(normalizedDecimal(value));
  return Number.isFinite(numeric) && numeric >= 0;
}

export function energyProfileNeedsUpdate(
  person: Person,
  profile: PersonEnergyProfile | null,
  values: PersonProfileEditorValues,
): boolean {
  if (profile === null) {
    return [values.sex, values.height, values.weight, values.activity, values.breakfast].some(
      (value) => Boolean(value.trim()),
    );
  }

  if (values.birthDate !== (person.birth_date ?? "") || values.timezone !== person.timezone) {
    return true;
  }
  if (
    values.sex !== profile.sex_for_energy_calculation ||
    values.activity !== profile.activity_level ||
    values.goal !== profile.goal_type
  ) {
    return true;
  }
  if (
    !sameDecimal(values.height, profile.height_cm) ||
    !sameDecimal(values.weight, profile.weight_kg) ||
    !sameDecimal(values.breakfast, profile.standard_breakfast_kcal)
  ) {
    return true;
  }
  if (values.goal === "maintain") {
    return profile.target_rate_kg_per_week !== null;
  }
  return (
    profile.target_rate_kg_per_week === null ||
    !sameDecimal(values.rate, profile.target_rate_kg_per_week)
  );
}

function errorText(error: unknown): string {
  if (error instanceof ApiError) return `${error.message} (HTTP ${error.status})`;
  return error instanceof Error ? error.message : String(error);
}

export default function PersonProfileEditor({
  person,
  profile,
  onCancel,
  onSaved,
}: {
  person: Person;
  profile: PersonEnergyProfile | null;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const timezones = useMemo(supportedTimezones, []);
  const [values, setValues] = useState<PersonProfileEditorValues>(() =>
    initialValues(person, profile),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update<K extends keyof PersonProfileEditorValues>(
    key: K,
    value: PersonProfileEditorValues[K],
  ) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!values.firstName.trim()) {
      setError(copy.requiredName);
      return;
    }

    const shouldUpdateEnergy = energyProfileNeedsUpdate(person, profile, values);
    let energyProfile: PersonEnergyProfileCreate | undefined;

    if (shouldUpdateEnergy) {
      if (!values.birthDate) {
        setError(copy.requiredBirth);
        return;
      }
      if (
        !values.sex ||
        !values.height.trim() ||
        !values.weight.trim() ||
        !values.activity ||
        !values.breakfast.trim()
      ) {
        setError(copy.incompleteEnergy);
        return;
      }
      if (!positive(values.height) || !positive(values.weight) || !nonNegative(values.breakfast)) {
        setError(copy.invalidNumbers);
        return;
      }
      if (values.goal !== "maintain" && !positive(values.rate)) {
        setError(copy.rateRequired);
        return;
      }
      energyProfile = {
        sex_for_energy_calculation: values.sex,
        height_cm: normalizedDecimal(values.height),
        weight_kg: normalizedDecimal(values.weight),
        activity_level: values.activity,
        goal_type: values.goal,
        target_rate_kg_per_week:
          values.goal === "maintain" ? null : normalizedDecimal(values.rate),
        standard_breakfast_kcal: normalizedDecimal(values.breakfast),
      };
    }

    setBusy(true);
    try {
      await updatePerson(person.id, {
        first_name: values.firstName.trim(),
        last_name: values.lastName.trim() || null,
        birth_date: values.birthDate || null,
        timezone: values.timezone,
        ...(energyProfile ? { energy_profile: energyProfile } : {}),
      });
      onSaved();
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="person-profile-form" onSubmit={submit}>
      {error ? (
        <div className="error-banner" role="alert">
          <strong>{copy.error}</strong>
          <span>{error}</span>
        </div>
      ) : null}

      <div className="person-profile-form__grid">
        <label className="field">
          <span>{copy.firstName}</span>
          <input value={values.firstName} onChange={(event) => update("firstName", event.target.value)} />
        </label>
        <label className="field">
          <span>{copy.lastName}</span>
          <input value={values.lastName} onChange={(event) => update("lastName", event.target.value)} />
        </label>
        <label className="field">
          <span>{copy.birthDate}</span>
          <input type="date" value={values.birthDate} onChange={(event) => update("birthDate", event.target.value)} />
        </label>
        <label className="field">
          <span>{copy.timezone}</span>
          <select value={values.timezone} onChange={(event) => update("timezone", event.target.value)}>
            {timezones.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="person-profile-form__section">
        <div>
          <h3>{copy.energy}</h3>
          <p>{copy.energyHelp}</p>
        </div>
        <div className="person-profile-form__grid">
          <label className="field">
            <span>{copy.sex}</span>
            <select
              value={values.sex}
              onChange={(event) =>
                update("sex", event.target.value as PersonProfileEditorValues["sex"])
              }
            >
              <option value="">—</option>
              <option value="male">{copy.male}</option>
              <option value="female">{copy.female}</option>
            </select>
          </label>
          <label className="field">
            <span>{copy.height}</span>
            <input inputMode="decimal" value={values.height} onChange={(event) => update("height", event.target.value)} />
          </label>
          <label className="field">
            <span>{copy.weight}</span>
            <input inputMode="decimal" value={values.weight} onChange={(event) => update("weight", event.target.value)} />
          </label>
          <label className="field">
            <span>{copy.activity}</span>
            <select
              value={values.activity}
              onChange={(event) =>
                update("activity", event.target.value as PersonProfileEditorValues["activity"])
              }
            >
              <option value="">—</option>
              <option value="sedentary">{copy.sedentary}</option>
              <option value="light">{copy.light}</option>
              <option value="moderate">{copy.moderate}</option>
              <option value="active">{copy.active}</option>
              <option value="very_active">{copy.very_active}</option>
            </select>
          </label>
          <label className="field">
            <span>{copy.goal}</span>
            <select
              value={values.goal}
              onChange={(event) => update("goal", event.target.value as NutritionGoalType)}
            >
              <option value="maintain">{copy.maintain}</option>
              <option value="lose">{copy.lose}</option>
              <option value="gain">{copy.gain}</option>
            </select>
          </label>
          <label className="field">
            <span>{copy.rate}</span>
            <input
              disabled={values.goal === "maintain"}
              inputMode="decimal"
              value={values.goal === "maintain" ? "" : values.rate}
              onChange={(event) => update("rate", event.target.value)}
            />
          </label>
          <label className="field">
            <span>{copy.breakfast}</span>
            <input inputMode="decimal" value={values.breakfast} onChange={(event) => update("breakfast", event.target.value)} />
          </label>
        </div>
      </div>

      <div className="person-profile-form__actions">
        <button className="button primary" disabled={busy} type="submit">
          {busy ? copy.saving : copy.save}
        </button>
        <button className="button ghost" disabled={busy} onClick={onCancel} type="button">
          {copy.cancel}
        </button>
      </div>
    </form>
  );
}
