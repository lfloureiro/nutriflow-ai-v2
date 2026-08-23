import { useState, type FormEvent } from "react";

import { ApiError } from "./api/client";
import { createFamilyPerson, getPersonEnergyProfile } from "./api/setupClient";
import type {
  ActivityLevel,
  EnergyCalculationSex,
  MealDiscoverySource,
  NutritionGoalType,
  PersonEnergyProfile,
} from "./api/setupTypes";
import { useI18n } from "./i18n";

const SOURCE_OPTIONS: MealDiscoverySource[] = [
  "shared_recipes",
  "uber_eats",
  "glovo",
  "restaurants",
];

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
    mealSources: "Onde procurar refeições para esta pessoa?",
    inheritSources: "Usar as opções da família",
    overrideHelp: "Desativa apenas se esta pessoa usar providers, morada ou zona diferentes.",
    shared_recipes: "Receitas partilhadas",
    uber_eats: "Uber Eats",
    glovo: "Glovo",
    restaurants: "Restaurantes na área",
    deliveryAddress: "Morada de entrega desta pessoa",
    restaurantArea: "Área de restaurantes desta pessoa",
    providerNote: "Uber Eats e Glovo só ficam live quando a integração oficial estiver configurada.",
    sourceRequired: "Escolhe pelo menos uma origem de refeições.",
    deliveryAddressRequired: "Indica a morada de entrega desta pessoa.",
    restaurantAreaRequired: "Indica a área onde procurar restaurantes.",
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
    mealSources: "Where should meals be discovered for this person?",
    inheritSources: "Use family options",
    overrideHelp: "Disable only if this person uses different providers, address or area.",
    shared_recipes: "Shared recipes",
    uber_eats: "Uber Eats",
    glovo: "Glovo",
    restaurants: "Restaurants in the area",
    deliveryAddress: "This person's delivery address",
    restaurantArea: "This person's restaurant area",
    providerNote: "Uber Eats and Glovo become live only when the official integration is configured.",
    sourceRequired: "Choose at least one meal source.",
    deliveryAddressRequired: "Enter this person's delivery address.",
    restaurantAreaRequired: "Enter the area where restaurants should be discovered.",
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
  const [inheritSources, setInheritSources] = useState(true);
  const [sources, setSources] = useState<MealDiscoverySource[]>(["shared_recipes"]);
  const [deliveryAddress, setDeliveryAddress] = useState("");
  const [restaurantArea, setRestaurantArea] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<PersonEnergyProfile | null>(null);

  const wantsDelivery = sources.includes("uber_eats") || sources.includes("glovo");
  const wantsRestaurants = sources.includes("restaurants");

  function toggleSource(source: MealDiscoverySource) {
    setSources((current) =>
      current.includes(source)
        ? current.filter((item) => item !== source)
        : [...current, source],
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setProfile(null);
    if (!inheritSources && sources.length === 0) {
      setError(copy.sourceRequired);
      return;
    }
    if (!inheritSources && wantsDelivery && !deliveryAddress.trim()) {
      setError(copy.deliveryAddressRequired);
      return;
    }
    if (!inheritSources && wantsRestaurants && !restaurantArea.trim()) {
      setError(copy.restaurantAreaRequired);
      return;
    }
    setBusy(true);
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
        meal_discovery: inheritSources
          ? null
          : {
              meal_discovery_sources: sources,
              delivery_address: deliveryAddress.trim() || null,
              restaurant_area: restaurantArea.trim() || null,
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
        <section className="person-discovery-setup">
          <div>
            <strong>{copy.mealSources}</strong>
            <p className="muted compact">{copy.overrideHelp}</p>
          </div>
          <label className="ingredient-check">
            <input checked={inheritSources} onChange={(event) => setInheritSources(event.target.checked)} type="checkbox" />
            <span>{copy.inheritSources}</span>
          </label>
          {!inheritSources ? (
            <>
              <div className="family-source-grid">
                {SOURCE_OPTIONS.map((source) => (
                  <label className={`recommend-source-card ${sources.includes(source) ? "selected" : ""}`} key={source}>
                    <input checked={sources.includes(source)} onChange={() => toggleSource(source)} type="checkbox" />
                    <span><strong>{copy[source]}</strong></span>
                  </label>
                ))}
              </div>
              {wantsDelivery ? <label className="field"><span>{copy.deliveryAddress}</span><input required value={deliveryAddress} onChange={(event) => setDeliveryAddress(event.target.value)} /></label> : null}
              {wantsRestaurants ? <label className="field"><span>{copy.restaurantArea}</span><input required value={restaurantArea} onChange={(event) => setRestaurantArea(event.target.value)} /></label> : null}
              {(sources.includes("uber_eats") || sources.includes("glovo")) ? <small className="muted">{copy.providerNote}</small> : null}
            </>
          ) : null}
        </section>
        <p className="muted compact">{copy.adultHelp}</p>
        <div className="button-row">
          <button className="button primary" disabled={busy} type="submit">{busy ? copy.saving : copy.save}</button>
          <button className="button ghost" disabled={busy} onClick={onCancel} type="button">{copy.cancel}</button>
        </div>
      </form>
    </section>
  );
}
