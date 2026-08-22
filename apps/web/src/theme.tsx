import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";

export type Appearance = "system" | "light" | "dark";

type ThemeValue = {
  appearance: Appearance;
  setAppearance: (appearance: Appearance) => void;
};

const ThemeContext = createContext<ThemeValue | null>(null);

function initialAppearance(): Appearance {
  const stored = window.localStorage.getItem("nutriflow-appearance");
  return stored === "light" || stored === "dark" || stored === "system" ? stored : "system";
}

function resolvedAppearance(appearance: Appearance): "light" | "dark" {
  if (appearance !== "system") {
    return appearance;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeProvider({ children }: PropsWithChildren) {
  const [appearance, setAppearanceState] = useState<Appearance>(initialAppearance);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      document.documentElement.dataset.theme = resolvedAppearance(appearance);
      document.documentElement.style.colorScheme = resolvedAppearance(appearance);
    };

    apply();
    if (appearance === "system") {
      media.addEventListener("change", apply);
      return () => media.removeEventListener("change", apply);
    }
    return undefined;
  }, [appearance]);

  const setAppearance = useCallback((nextAppearance: Appearance) => {
    window.localStorage.setItem("nutriflow-appearance", nextAppearance);
    setAppearanceState(nextAppearance);
  }, []);

  const value = useMemo(
    () => ({ appearance, setAppearance }),
    [appearance, setAppearance],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeValue {
  const value = useContext(ThemeContext);
  if (value === null) {
    throw new Error("useTheme must be used inside ThemeProvider.");
  }
  return value;
}
