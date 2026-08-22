import type {
  Ingredient,
  IngredientCreate,
  IngredientUpdate,
} from "./ingredientTypes";
import type {
  FamilyDashboard,
  FamilyMeals,
  Person,
  PlanningBootstrap,
  PracticalRecommendationRequest,
  PracticalRecommendationRun,
  RecommendationDecision,
  RecommendationDecisionRequest,
} from "./types";

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function normalizeApiBaseUrl(value: string): string {
  return value.trim().replace(/\/+$/, "");
}

export function buildApiUrl(path: string, baseUrl = configuredApiBaseUrl): string {
  const normalizedBase = normalizeApiBaseUrl(baseUrl);
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

export function familyDashboardPath(familyId: string, onDate?: string): string {
  const base = `/api/families/${encodeURIComponent(familyId)}/dashboard`;
  if (!onDate) {
    return base;
  }
  const query = new URLSearchParams({ on_date: onDate });
  return `${base}?${query.toString()}`;
}

export function familyMealsPath(familyId: string, startDate?: string, days = 7): string {
  const base = `/api/families/${encodeURIComponent(familyId)}/meals`;
  const query = new URLSearchParams({ days: String(days) });
  if (startDate) {
    query.set("start_date", startDate);
  }
  return `${base}?${query.toString()}`;
}

export function familyIngredientsPath(
  familyId: string,
  query?: string,
  includeInactive = false,
): string {
  const base = `/api/families/${encodeURIComponent(familyId)}/ingredients`;
  const params = new URLSearchParams();
  if (query?.trim()) {
    params.set("q", query.trim());
  }
  if (includeInactive) {
    params.set("include_inactive", "true");
  }
  const suffix = params.toString();
  return suffix ? `${base}?${suffix}` : base;
}

export function planningBootstrapPath(personId: string, scheduledAt: string): string {
  const encodedPersonId = encodeURIComponent(personId);
  const query = new URLSearchParams({ scheduled_at: scheduledAt });
  return `/api/persons/${encodedPersonId}/planning-bootstrap?${query.toString()}`;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    // A non-JSON error body falls through to the HTTP status text below.
  }
  return response.statusText || `HTTP ${response.status}`;
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(buildApiUrl(path), {
    ...init,
    headers,
  });

  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function getFamilyDashboard(familyId: string, onDate?: string): Promise<FamilyDashboard> {
  return apiRequest<FamilyDashboard>(familyDashboardPath(familyId, onDate));
}

export function getFamilyMeals(
  familyId: string,
  startDate?: string,
  days = 7,
): Promise<FamilyMeals> {
  return apiRequest<FamilyMeals>(familyMealsPath(familyId, startDate, days));
}

export function listFamilyIngredients(
  familyId: string,
  query?: string,
  includeInactive = false,
): Promise<Ingredient[]> {
  return apiRequest<Ingredient[]>(familyIngredientsPath(familyId, query, includeInactive));
}

export function createFamilyIngredient(
  familyId: string,
  payload: IngredientCreate,
): Promise<Ingredient> {
  return apiRequest<Ingredient>(familyIngredientsPath(familyId), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateFamilyIngredient(
  familyId: string,
  ingredientId: string,
  payload: IngredientUpdate,
): Promise<Ingredient> {
  return apiRequest<Ingredient>(
    `${familyIngredientsPath(familyId)}/${encodeURIComponent(ingredientId)}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );
}

export function deactivateFamilyIngredient(
  familyId: string,
  ingredientId: string,
): Promise<void> {
  return apiRequest<void>(
    `${familyIngredientsPath(familyId)}/${encodeURIComponent(ingredientId)}`,
    { method: "DELETE" },
  );
}

export function listFamilyPersons(familyId: string): Promise<Person[]> {
  return apiRequest<Person[]>(`/api/families/${encodeURIComponent(familyId)}/persons`);
}

export function getPlanningBootstrap(
  personId: string,
  scheduledAt: string,
): Promise<PlanningBootstrap> {
  return apiRequest<PlanningBootstrap>(planningBootstrapPath(personId, scheduledAt));
}

export function requestPracticalRecommendation(
  personId: string,
  payload: PracticalRecommendationRequest,
): Promise<PracticalRecommendationRun> {
  return apiRequest<PracticalRecommendationRun>(
    `/api/persons/${encodeURIComponent(personId)}/meal-recommendations/practical`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function submitRecommendationDecision(
  optionId: string,
  payload: RecommendationDecisionRequest,
): Promise<RecommendationDecision> {
  return apiRequest<RecommendationDecision>(
    `/api/recommendation-options/${encodeURIComponent(optionId)}/decision`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}
