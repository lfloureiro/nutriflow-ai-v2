import type {CSSProperties} from "react";
import {type AvatarPreference, type AvatarStage} from "./avatarPreferences";
/** Stable, presentation-only identity. Never encodes health, suitability or diagnosis. */
export function avatarTone(identity: string): number {
  let hash = 0;
  for (const character of identity) hash = ((hash * 31) + character.codePointAt(0)!) >>> 0;
  return hash % 6;
}
export function avatarInitials(name: string): string {
  return name.trim().split(/\s+/).filter(Boolean).slice(0, 2).map(word => Array.from(word)[0]).join("").toLocaleUpperCase();
}
export function avatarAgeGroup(age?: number | null): AvatarStage {
  if(age == null || !Number.isFinite(age) || age < 0)return "unknown";
  return age < 13 ? "child" : age < 18 ? "teen" : age < 30 ? "young" : age < 45 ? "adult" : age < 65 ? "mature" : "senior";
}
export function familySkinPalette(familyIdentity: string): string {
  return ["#e4b28e", "#dca782", "#e9bf9d"][avatarTone(familyIdentity)%3]!;
}
export default function PersonAvatar({identity, name, familyIdentity = "family", age, sex, size = "md", decorative = false, selected = false, preview, appearance: persisted}: {
  identity: string; name: string; familyIdentity?: string; age?: number | null; sex?: "male" | "female" | null; size?: "sm" | "md" | "lg"; decorative?: boolean; selected?: boolean; preview?: AvatarPreference; appearance?: AvatarPreference | null;
}) {
  const preference = preview ?? persisted ?? {};
  const group = preference.stage ?? avatarAgeGroup(age);
  const style = preference.style ?? sex ?? "neutral";
  const variant = preference.variant ?? avatarTone(identity);
  const child = group === "child";
  const older = group === "mature" || group === "senior";
  const adult = older || group === "adult";
  const feminine = style === "female";
  const face = child ? "M18 28Q18 14 32 14T46 28Q46 44 32 45Q18 44 18 28" : feminine
    ? "M19 26Q19 12 32 12T45 26L44 36Q40 47 32 48Q24 47 20 36Z"
    : adult ? "M17 25Q17 11 32 11T47 25L46 37L40 46Q32 51 24 46L18 37Z" : "M19 27Q19 12 32 12T45 27L44 36Q41 46 32 47Q23 46 20 36Z";
  const hair = feminine ? ["M16 31Q11 5 32 5T48 34L42 21Q35 24 26 14L22 28Z", "M16 29Q10 6 30 5Q51 2 49 34L44 21Q32 22 22 15Z", "M16 29Q11 8 30 5Q47 3 49 29L43 24L41 13Q31 22 20 20Z"][variant % 3]!
    : older ? ["M17 29Q12 8 29 7Q48 3 48 28L43 19Q34 23 23 16L21 29Z", "M17 28Q13 11 24 9L32 13L40 9Q51 11 47 28L43 20L35 18L25 18L21 22Z", "M17 29Q12 9 27 9L32 13L37 9Q51 8 47 29L43 19L39 16L34 18L25 16L21 23Z"][variant % 3]!
    : ["M17 27Q11 10 22 10L27 4L32 8L39 5Q53 10 47 28L42 19L33 17L23 21Z", "M17 29Q11 8 28 7Q49 2 48 27L43 19Q32 25 21 18L21 29Z", "M17 27Q12 7 30 7Q49 3 48 27L43 20L43 14L22 14L21 27Z"][variant % 3]!;
  const appearance = {"--avatar-skin":familySkinPalette(familyIdentity), "--avatar-hair":group === "senior" ? "#b6b1ac" : group === "mature" ? "#76716d" : ["#362b29", "#634332", "#332d32", "#7b5339", "#282a31", "#865e40"][variant % 6]} as CSSProperties;
  return <span style={appearance} data-age-group={group} data-hair={style === "female" ? "long" : style === "male" ? "short" : "neutral"} data-variant={variant} className={`nf-avatar nf-avatar--${size}${selected ? " is-selected" : ""}`} data-tone={avatarTone(identity)} role={decorative ? undefined : "img"} aria-label={decorative ? undefined : name} aria-hidden={decorative || undefined}>
    <svg className="nf-avatar-portrait" viewBox="0 0 64 64" aria-hidden="true">
      {feminine && <path d={variant % 3 === 0 ? "M14 29Q9 5 32 5T50 29L52 58L12 58Z" : variant % 3 === 1 ? "M15 27Q10 5 32 5T49 27L47 47L17 47Z" : "M15 29Q9 5 32 5T49 29L50 54Q42 60 39 49L22 49L15 54Z"} className="nf-avatar-hair"/>}
      <path d={child ? "M13 64Q13 49 32 49T51 64Z" : feminine ? "M11 64Q12 50 27 48L37 48Q52 50 53 64Z" : "M6 64Q8 50 26 47H38Q56 50 58 64Z"} className="nf-avatar-shirt"/>
      <path d="M27 39H37V51Q32 56 27 51Z" className="nf-avatar-skin"/>
      <path d={feminine ? "M23 49L32 58L41 49" : adult ? "M22 49L28 58L32 53L36 58L42 49" : "M24 49Q32 58 40 49"} fill="none" stroke="#fff" strokeOpacity=".6" strokeWidth="2"/>
      <ellipse cx="18" cy="30" rx="3" ry="5" className="nf-avatar-skin"/><ellipse cx="46" cy="30" rx="3" ry="5" className="nf-avatar-skin"/>
      <path d={face} className="nf-avatar-skin"/>
      {style === "male" && adult && <path d="M18 33L22 37L27 40H37L42 37L46 33L45 40L39 47Q32 51 25 47L19 40Z" className="nf-avatar-hair" opacity={older ? ".85" : ".4"}/>}
      <path d={hair} className="nf-avatar-hair"/>
      {variant === 3 && <path d={feminine ? "M15 16Q8 10 12 6Q17 2 21 10M45 16Q54 9 49 5Q44 1 41 10" : "M21 13L25 7L30 11L35 6L41 14"} fill="none" className="nf-avatar-hair-accent" strokeWidth="4" strokeLinecap="round"/>}
      {variant === 4 && <path d={feminine ? "M15 18Q7 27 17 34M49 18Q57 27 47 34" : "M20 16Q26 12 44 14"} fill="none" className="nf-avatar-hair-accent" strokeWidth="4" strokeLinecap="round"/>}
      {variant === 5 && <path d={feminine ? "M46 17Q60 11 56 30Q55 36 49 42L47 27Z" : "M22 16L26 14M28 15L32 13M34 14L38 13"} className={feminine ? "nf-avatar-hair" : "nf-avatar-hair-accent"} fill={feminine ? undefined : "none"} strokeWidth="2"/>}
      {older && <g fill="none" stroke="#946c56" strokeWidth=".85" strokeLinecap="round"><path d="M26 21H38M26 18H37M20 33L23 34M41 34L44 33M24 36L23 39M40 36L41 39"/></g>}
      <g fill="none" stroke="#49362f" strokeWidth={style === "male" ? "2.2" : "1.3"} strokeLinecap="round"><path d={older ? "M23 26L28 25M36 25L41 26" : "M23 25Q26 23 29 25M35 25Q38 23 41 25"}/></g>
      <g className="nf-avatar-eyes" fill="#392c2b"><ellipse cx="26" cy="29" rx="1.3" ry={child ? "2" : "1.6"}/><ellipse cx="38" cy="29" rx="1.3" ry={child ? "2" : "1.6"}/></g>
      {feminine && <path d="M23 28L25 29M39 29L41 28" fill="none" stroke="#49362f" strokeWidth="1.2"/>}
      <path d={child ? "M31 32L30 35H33" : "M32 30L30 35L33 36"} fill="none" stroke="#b37c61" strokeWidth="1" strokeLinecap="round"/>
      <path d={feminine ? "M28 39Q32 43 36 39Q32 41 28 39" : "M28 40Q32 43 36 40"} fill={feminine ? "#a95e55" : "none"} stroke="#864f43" strokeWidth="1.2" strokeLinecap="round"/>
      {((older && variant % 2 === 0) || variant === 4) && <g fill="none" stroke="#403b40" strokeWidth="1.25"><rect x="20" y="26" width="11" height="8" rx="3"/><rect x="33" y="26" width="11" height="8" rx="3"/><path d="M31 29H33M17 28H20M44 28H47"/></g>}
    </svg>
    <span className="nf-avatar-initials">{avatarInitials(name)}</span>
  </span>;
}
