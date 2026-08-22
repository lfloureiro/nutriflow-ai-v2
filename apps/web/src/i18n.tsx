import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";

export type Locale = "pt-PT" | "en";

const messages = {
  "pt-PT": {
    "app.brand": "NutriFlow AI",
    "app.tagline": "Planeamento alimentar adaptado ao teu dia real.",
    "nav.language": "Idioma",
    "nav.appearance": "Aparência",
    "theme.system": "Sistema",
    "theme.light": "Claro",
    "theme.dark": "Escuro",
    "setup.title": "1. Escolher pessoa",
    "setup.help": "Indica a família para carregar as pessoas disponíveis.",
    "setup.familyId": "ID da família",
    "setup.loadPeople": "Carregar pessoas",
    "setup.person": "Pessoa",
    "setup.choosePerson": "Escolhe uma pessoa",
    "planner.title": "2. Contexto da refeição",
    "planner.help": "Este primeiro vertical slice usa IDs explícitos do estado diário e das composições persistidas.",
    "planner.stateId": "ID do estado nutricional diário",
    "planner.date": "Data de planeamento",
    "planner.time": "Hora da refeição",
    "planner.mealType": "Tipo de refeição",
    "planner.location": "Local",
    "planner.availableMinutes": "Minutos disponíveis",
    "planner.kitchen": "Cozinha disponível",
    "planner.unknown": "Desconhecido",
    "planner.yes": "Sim",
    "planner.no": "Não",
    "planner.sources": "Fontes a considerar",
    "planner.candidates": "Candidatos",
    "planner.addCandidate": "Adicionar candidato",
    "planner.candidateKind": "Tipo",
    "planner.food": "Alimento / prato",
    "planner.recipe": "Receita",
    "planner.compositionId": "ID da composição",
    "planner.quantity": "Quantidade",
    "planner.unit": "Unidade",
    "planner.remove": "Remover",
    "planner.recommend": "Obter recomendações",
    "source.home": "Casa",
    "source.pantry": "Despensa",
    "source.restaurant": "Restaurante",
    "source.delivery": "Delivery",
    "source.store": "Loja",
    "status.loadingPeople": "A carregar pessoas…",
    "status.loadingRecommendation": "A calcular recomendações…",
    "status.savingDecision": "A guardar decisão…",
    "results.title": "3. Recomendações",
    "results.run": "Execução",
    "results.eligible": "Elegível",
    "results.excluded": "Excluído",
    "results.kcal": "kcal",
    "results.nutrients": "Nutrientes",
    "results.offers": "Ofertas disponíveis",
    "results.provider": "Fornecedor",
    "results.total": "Total conhecido",
    "results.accept": "Aceitar",
    "results.reject": "Rejeitar",
    "results.accepted": "Aceite",
    "results.rejected": "Rejeitada",
    "results.mealCreated": "Refeição criada no plano",
    "results.noOffers": "Sem ofertas comerciais ativas.",
    "results.reasons": "Motivos",
    "results.explanation": "Explicação",
    "empty.results": "Preenche o contexto e pede uma recomendação para veres opções aqui.",
    "error.title": "Não foi possível concluir a operação",
    "validation.familyRequired": "Indica o ID da família.",
    "validation.personRequired": "Escolhe uma pessoa.",
    "validation.stateRequired": "Indica o ID do estado nutricional diário.",
    "validation.candidateRequired": "Adiciona pelo menos um candidato válido.",
    "validation.compositionRequired": "Todos os candidatos precisam de um ID de composição.",
    "footer.devNote": "Primeiro vertical slice web — ainda sem autenticação nem descoberta automática de catálogo/estado diário.",
  },
  en: {
    "app.brand": "NutriFlow AI",
    "app.tagline": "Nutrition planning adapted to your real day.",
    "nav.language": "Language",
    "nav.appearance": "Appearance",
    "theme.system": "System",
    "theme.light": "Light",
    "theme.dark": "Dark",
    "setup.title": "1. Choose a person",
    "setup.help": "Enter a Family ID to load the available people.",
    "setup.familyId": "Family ID",
    "setup.loadPeople": "Load people",
    "setup.person": "Person",
    "setup.choosePerson": "Choose a person",
    "planner.title": "2. Meal context",
    "planner.help": "This first vertical slice uses explicit persisted DailyNutritionState and composition IDs.",
    "planner.stateId": "Daily nutrition state ID",
    "planner.date": "Planning date",
    "planner.time": "Meal time",
    "planner.mealType": "Meal type",
    "planner.location": "Location",
    "planner.availableMinutes": "Available minutes",
    "planner.kitchen": "Kitchen available",
    "planner.unknown": "Unknown",
    "planner.yes": "Yes",
    "planner.no": "No",
    "planner.sources": "Sources to consider",
    "planner.candidates": "Candidates",
    "planner.addCandidate": "Add candidate",
    "planner.candidateKind": "Type",
    "planner.food": "Food / dish",
    "planner.recipe": "Recipe",
    "planner.compositionId": "Composition ID",
    "planner.quantity": "Quantity",
    "planner.unit": "Unit",
    "planner.remove": "Remove",
    "planner.recommend": "Get recommendations",
    "source.home": "Home",
    "source.pantry": "Pantry",
    "source.restaurant": "Restaurant",
    "source.delivery": "Delivery",
    "source.store": "Store",
    "status.loadingPeople": "Loading people…",
    "status.loadingRecommendation": "Calculating recommendations…",
    "status.savingDecision": "Saving decision…",
    "results.title": "3. Recommendations",
    "results.run": "Run",
    "results.eligible": "Eligible",
    "results.excluded": "Excluded",
    "results.kcal": "kcal",
    "results.nutrients": "Nutrients",
    "results.offers": "Available offers",
    "results.provider": "Provider",
    "results.total": "Known total",
    "results.accept": "Accept",
    "results.reject": "Reject",
    "results.accepted": "Accepted",
    "results.rejected": "Rejected",
    "results.mealCreated": "Meal created in the plan",
    "results.noOffers": "No active commercial offers.",
    "results.reasons": "Reasons",
    "results.explanation": "Explanation",
    "empty.results": "Fill in the context and request a recommendation to see options here.",
    "error.title": "The operation could not be completed",
    "validation.familyRequired": "Enter the Family ID.",
    "validation.personRequired": "Choose a person.",
    "validation.stateRequired": "Enter the daily nutrition state ID.",
    "validation.candidateRequired": "Add at least one valid candidate.",
    "validation.compositionRequired": "Every candidate needs a composition ID.",
    "footer.devNote": "First web vertical slice — authentication and automatic catalogue/daily-state discovery are not implemented yet.",
  },
} as const;

type MessageKey = keyof (typeof messages)["pt-PT"];

type I18nValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey) => string;
};

const I18nContext = createContext<I18nValue | null>(null);

function initialLocale(): Locale {
  const stored = window.localStorage.getItem("nutriflow-locale");
  if (stored === "pt-PT" || stored === "en") {
    return stored;
  }
  return navigator.language.toLowerCase().startsWith("pt") ? "pt-PT" : "en";
}

export function translate(locale: Locale, key: MessageKey): string {
  return messages[locale][key];
}

export function I18nProvider({ children }: PropsWithChildren) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback((nextLocale: Locale) => {
    window.localStorage.setItem("nutriflow-locale", nextLocale);
    setLocaleState(nextLocale);
  }, []);

  const value = useMemo<I18nValue>(
    () => ({
      locale,
      setLocale,
      t: (key) => translate(locale, key),
    }),
    [locale, setLocale],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const value = useContext(I18nContext);
  if (value === null) {
    throw new Error("useI18n must be used inside I18nProvider.");
  }
  return value;
}
