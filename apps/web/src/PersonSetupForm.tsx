import { useState, type FormEvent } from "react";

import { ApiError } from "./api/client";
import { createFamilyPerson, getPersonEnergyProfile } from "./api/setupClient";
import type {
  ActivityLevel,
  EnergyCalculationSex,
  NutritionGoalType,
  PersonEnergyProfile,
} from "./api/setupTypes";
import { useI18n } from "./i18n";

const COPY = {
  "pt-PT": {
    title: "Adicionar pessoa",
    help: "Estes dados permitem estimar as necessidades energéticas e criar o intervalo calórico diário.",
    firstName: "Nome",
    lastName: "Apelido",
    birthDate: "Data de nascimento",
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
    breakfastHelp: "Usado apenas como estimativa quando o pequeno-almoço não está declarado. Usa 0 se normalmente não toma pequeno-almoço.",
    adultHelp: "O cálculo automático atual usa Mifflin-St Jeor e está limitado a adultos (18+).",
    save: "Criar pessoa",
    saving: "A criar…",
    cancel: "Cancelar",
    result: "Intervalo diário calculado",
    tdee: "Gasto diário estimado",
    error: "Não foi possível criar a pessoa",
  },
  en: {
    title: "Add person",
    help: "These details are used to estimate energy needs and create the daily calorie range.",
    firstName: "First name",
    lastName: "Last name",
    birthDate: "Date of birth",
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
    breakfastHelp: "Used only as an estimate when breakfast is not declared. Use 0 if breakfast is normally skipped.",
    adultHelp: "The current automatic calculation uses Mifflin-St Jeor and is limited to adults (18+).",
    save: "Create person",
    saving: "Creating…",
    cancel: "Cancel",
    result: "Calculated daily range",
    tdee: "Estimated daily expenditure",
    error: "Could not create person",
  },
} as const;

function errorText(error: unknown): string {
  if (error instanceof ApiError) return `${error.message} (HTTP ${error.status})`;
  return error instanceof Error ? error.message : String(error);
}

function kcal(value: string, locale: string): string {
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(Number(value))} kcal`;
}

export default function PersonSetupForm({
  familyId,
  familyTimezone,
  onCancel,
  onCreated,
}: {
  familyId: string;
  familyTimezone: string;
  onCancel: () => void;
  onCreated: () => void;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [sex, setSex] = useState<EnergyCalculationSex>("male");
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");
  const [activity, setActivity] = useState<ActivityLevel>("sedentary");
  const [goal, setGoal] = useState<NutritionGoalType>("maintain");
  const [rate, setRate] = useState("0.5");
  const [breakfast, setBreakfast] = useState("350");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<PersonEnergyProfile | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setProfile(null);
    try {
      const created = await createFamilyPerson(familyId, {
        first_name: firstName.trim(),
        last_name: lastName.trim() || null,
        birth_date: birthDate,
        preferred_locale: locale,
        timezone: familyTimezone,
        energy_profile: {
          sex_for_energy_calculation: sex,
          height_cm: height,
          weight_kg: weight,
          activity_level: activity,
          goal_type: goal,
          target_rate_kg_per_week: goal === "maintain" ? null : rate,
          standard_breakfast_kcal: breakfast,
        },
      });
      const energy = await getPersonEnergyProfile(created.id);
      setProfile(energy);
      onCreated();
    } catch (caught: unknown) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="person-setup-card">
      <header>
        <div>
          <span className="eyebrow">{copy.title}</span>
          <h2>{copy.title}</h2>
          <p>{copy.help}</p>
        </div>
      </header>
      {error ? <div className="error-banner" role="alert"><strong>{copy.error}</strong><span>{error}</span></div> : null}
      {profile ? (
        <div className="person-energy-result" role="status">
          <div><span>{copy.result}</span><strong>{kcal(profile.energy_min_kcal, locale)} – {kcal(profile.energy_max_kcal, locale)}</strong></div>
          <div><span>{copy.tdee}</span><strong>{kcal(profile.estimated_tdee_kcal, locale)}</strong></div>
        </div>
      ) : null}
      <form className="person-setup-form" onSubmit={submit}>
        <div className="form-grid two">
          <label className="field"><span>{copy.firstName}</span><input required value={firstName} onChange={(event) => setFirstName(event.target.value)} /></label>
          <label className="field"><span>{copy.lastName}</span><input value={lastName} onChange={(event) => setLastName(event.target.value)} /></label>
          <label className="field"><span>{copy.birthDate}</span><input required type="date" value={birthDate} onChange={(event) => setBirthDate(event.target.value)} /></label>
          <label className="field"><span>{copy.sex}</span><select value={sex} onChange={(event) => setSex(event.target.value as EnergyCalculationSex)}><option value="male">{copy.male}</option><option value="female">{copy.female}</option></select></label>
          <label className="field"><span>{copy.height}</span><input min="1" max="250" required type="number" step="0.1" value={height} onChange={(event) => setHeight(event.target.value)} /></label>
          <label className="field"><span>{copy.weight}</span><input min="1" max="500" required type="number" step="0.1" value={weight} onChange={(event) => setWeight(event.target.value)} /></label>
          <label className="field"><span>{copy.activity}</span><select value={activity} onChange={(event) => setActivity(event.target.value as ActivityLevel)}>{(["sedentary", "light", "moderate", "active", "very_active"] as ActivityLevel[]).map((value) => <option key={value} value={value}>{copy[value]}</option>)}</select></label>
          <label className="field"><span>{copy.goal}</span><select value={goal} onChange={(event) => setGoal(event.target.value as NutritionGoalType)}><option value="maintain">{copy.maintain}</option><option value="lose">{copy.lose}</option><option value="gain">{copy.gain}</option></select></label>
          {goal !== "maintain" ? <label className="field"><span>{copy.rate}</span><input min="0.1" max="1" required type="number" step="0.1" value={rate} onChange={(event) => setRate(event.target.value)} /></label> : null}
          <label className="field"><span>{copy.breakfast}</span><input min="0" max="1000" required type="number" step="10" value={breakfast} onChange={(event) => setBreakfast(event.target.value)} /><small>{copy.breakfastHelp}</small></label>
        </div>
        <p className="muted compact">{copy.adultHelp}</p>
        <div className="button-row">
          <button className="button primary" disabled={busy} type="submit">{busy ? copy.saving : copy.save}</button>
          <button className="button ghost" disabled={busy} onClick={onCancel} type="button">{copy.cancel}</button>
        </div>
      </form>
    </section>
  );
}
