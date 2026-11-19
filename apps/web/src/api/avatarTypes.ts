export type AvatarStage = "child" | "teen" | "young" | "adult" | "mature" | "senior" | "unknown";
export type AvatarStyle = "male" | "female" | "neutral";
export type AvatarPreference = {stage?: AvatarStage | null; style?: AvatarStyle | null; variant?: number | null};
