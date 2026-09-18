import { ApiError, buildApiUrl } from "./client";
import type {
  SharedWeeklyPlanProposal,
  SharedWeeklyPlanProposalRequest,
  SharedWeeklyPlanSlotAcceptance,
  SharedWeeklyPlanSlotAcceptanceRequest,
} from "./weeklyPlanningTypes";

const INTERACTIVE_MAX_COMBINATIONS = 256;

async function responseError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    // Fall through to the HTTP status text.
  }
  return response.statusText || `HTTP ${response.status}`;
}

export async function requestSharedWeeklyPlanProposal(
  familyId: string,
  payload: SharedWeeklyPlanProposalRequest,
): Promise<SharedWeeklyPlanProposal> {
  const path = `/api/families/${encodeURIComponent(familyId)}/weekly-planning/proposals`;
  const requestedBudget = payload.max_combinations ?? INTERACTIVE_MAX_COMBINATIONS;
  const interactivePayload: SharedWeeklyPlanProposalRequest = {
    ...payload,
    max_combinations: Math.min(requestedBudget, INTERACTIVE_MAX_COMBINATIONS),
  };
  const response = await fetch(buildApiUrl(path), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(interactivePayload),
  });
  if (!response.ok) {
    throw new ApiError(await responseError(response), response.status);
  }
  return (await response.json()) as SharedWeeklyPlanProposal;
}

export async function acceptSharedWeeklyPlanSlot(
  familyId: string,
  payload: SharedWeeklyPlanSlotAcceptanceRequest,
): Promise<SharedWeeklyPlanSlotAcceptance> {
  const path = `/api/families/${encodeURIComponent(familyId)}/weekly-planning/proposals/accept-slot`;
  const response = await fetch(buildApiUrl(path), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new ApiError(await responseError(response), response.status);
  }
  return (await response.json()) as SharedWeeklyPlanSlotAcceptance;
}
