import { ApiError, buildApiUrl } from "./client";
import type {
  NutritionPlanChatGPTPrompt,
  NutritionPlanDocumentExtraction,
  NutritionPlanImportConfirmationStatus,
  NutritionPlanImportCreate,
  NutritionPlanImportProposal,
  NutritionPlanImportSession,
} from "./nutritionPlanImportTypes";

async function errorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) return payload.detail;
  } catch {
    // Fall through to status text.
  }
  return response.statusText || `HTTP ${response.status}`;
}

async function jsonRequest<T>(url: string, init: RequestInit): Promise<T> {
  const response = await fetch(buildApiUrl(url), {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });
  if (!response.ok) throw new ApiError(await errorMessage(response), response.status);
  return (await response.json()) as T;
}

export async function extractNutritionPlanDocument(
  personId: string,
  file: File,
): Promise<NutritionPlanDocumentExtraction> {
  const body = new FormData();
  body.append("document", file);
  const response = await fetch(
    buildApiUrl(
      `/api/persons/${encodeURIComponent(personId)}/nutrition-plan-imports/extract-document`,
    ),
    {
      method: "POST",
      headers: { Accept: "application/json" },
      body,
    },
  );
  if (!response.ok) throw new ApiError(await errorMessage(response), response.status);
  return (await response.json()) as NutritionPlanDocumentExtraction;
}

export function getChatGPTNutritionPlanPrompt(
  personId: string,
  payload: NutritionPlanImportCreate,
): Promise<NutritionPlanChatGPTPrompt> {
  return jsonRequest<NutritionPlanChatGPTPrompt>(
    `/api/persons/${encodeURIComponent(personId)}/nutrition-plan-imports/chatgpt/prompt`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export function createChatGPTNutritionPlanImport(
  personId: string,
  payload: NutritionPlanImportCreate,
  responseText: string,
): Promise<NutritionPlanImportSession> {
  return jsonRequest<NutritionPlanImportSession>(
    `/api/persons/${encodeURIComponent(personId)}/nutrition-plan-imports/chatgpt`,
    {
      method: "POST",
      body: JSON.stringify({ plan: payload, response_text: responseText }),
    },
  );
}

export function createNutritionPlanImport(
  personId: string,
  payload: NutritionPlanImportCreate,
  mode: "ai" | "deterministic",
): Promise<NutritionPlanImportSession> {
  const suffix = mode === "ai" ? "/ai" : "";
  return jsonRequest<NutritionPlanImportSession>(
    `/api/persons/${encodeURIComponent(personId)}/nutrition-plan-imports${suffix}`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export function setNutritionPlanImportProposalStatus(
  personId: string,
  importId: string,
  proposalId: string,
  confirmationStatus: NutritionPlanImportConfirmationStatus,
): Promise<NutritionPlanImportProposal> {
  return jsonRequest<NutritionPlanImportProposal>(
    `/api/persons/${encodeURIComponent(personId)}/nutrition-plan-imports/${encodeURIComponent(importId)}/proposals/${encodeURIComponent(proposalId)}`,
    {
      method: "PATCH",
      body: JSON.stringify({ confirmation_status: confirmationStatus }),
    },
  );
}

export function applyNutritionPlanImport(
  personId: string,
  importId: string,
): Promise<NutritionPlanImportSession> {
  return jsonRequest<NutritionPlanImportSession>(
    `/api/persons/${encodeURIComponent(personId)}/nutrition-plan-imports/${encodeURIComponent(importId)}/apply`,
    { method: "POST" },
  );
}

export async function activateImportedNutritionPlan(
  personId: string,
  planId: string,
): Promise<void> {
  await jsonRequest<unknown>(
    `/api/persons/${encodeURIComponent(personId)}/nutrition-plans/${encodeURIComponent(planId)}`,
    { method: "PATCH", body: JSON.stringify({ status: "active" }) },
  );
}
