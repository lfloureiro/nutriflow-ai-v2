import type {AvatarPreference, AvatarStage, AvatarStyle} from "../api/avatarTypes";
export type {AvatarPreference, AvatarStage, AvatarStyle} from "../api/avatarTypes";
const stages: AvatarStage[] = ["child", "teen", "young", "adult", "mature", "senior", "unknown"];
const styles: AvatarStyle[] = ["male", "female", "neutral"];
export function parseAvatarPreference(raw: string | null): AvatarPreference {
  try {
    const value: unknown = JSON.parse(raw ?? "null");
    if (!value || typeof value !== "object") return {};
    const item = value as Record<string, unknown>;
    return {
      ...(stages.includes(item.stage as AvatarStage) ? {stage:item.stage as AvatarStage} : {}),
      ...(styles.includes(item.style as AvatarStyle) ? {style:item.style as AvatarStyle} : {}),
      ...(typeof item.variant === "number" && Number.isInteger(item.variant) && item.variant >= 0 && item.variant <= 5 ? {variant:item.variant} : {}),
    };
  } catch {return {};}
}
