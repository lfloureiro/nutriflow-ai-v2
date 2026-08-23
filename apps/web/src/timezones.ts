const PREFERRED_TIMEZONES = [
  "Europe/Lisbon",
  "Atlantic/Azores",
  "Europe/London",
  "Europe/Madrid",
  "Europe/Paris",
  "Europe/Berlin",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Sao_Paulo",
  "Asia/Dubai",
  "Asia/Shanghai",
  "Asia/Tokyo",
  "Australia/Sydney",
] as const;

const FALLBACK_TIMEZONES = [...PREFERRED_TIMEZONES];

export function supportedTimezones(): string[] {
  const intl = Intl as typeof Intl & {
    supportedValuesOf?: (key: "timeZone") => string[];
  };
  const available = intl.supportedValuesOf?.("timeZone") ?? FALLBACK_TIMEZONES;
  const unique = new Set(available);
  for (const timezone of PREFERRED_TIMEZONES) unique.add(timezone);

  const preferred = PREFERRED_TIMEZONES.filter((timezone) => unique.has(timezone));
  const remaining = [...unique]
    .filter((timezone) => !preferred.includes(timezone as (typeof PREFERRED_TIMEZONES)[number]))
    .sort((left, right) => left.localeCompare(right));
  return [...preferred, ...remaining];
}
