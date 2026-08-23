import { ApiError, buildApiUrl } from "./client";
import type {
  CreatedPerson,
  Family,
  FamilyCreate,
  PersonCreate,
  PersonEnergyProfile,
} from "./setupTypes";

async function setupRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body !== undefined) headers.set("Content-Type", "application/json");
  const response = await fetch(buildApiUrl(path), { ...init, headers });
  if (!response.ok) {
    let message = response.statusText || `HTTP ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string" && payload.detail) message = payload.detail;
    } catch {
      // Keep HTTP fallback.
    }
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as T;
}

export function createFamily(payload: FamilyCreate): Promise<Family> {
  return setupRequest<Family>("/api/families", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createFamilyPerson(familyId: string, payload: PersonCreate): Promise<CreatedPerson> {
  return setupRequest<CreatedPerson>(`/api/families/${encodeURIComponent(familyId)}/persons`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getPersonEnergyProfile(personId: string): Promise<PersonEnergyProfile> {
  return setupRequest<PersonEnergyProfile>(
    `/api/persons/${encodeURIComponent(personId)}/energy-profile`,
  );
}
