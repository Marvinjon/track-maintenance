import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

export type ColorSchemePreference = "light" | "dark" | "system";

const STORAGE_KEY = "track_maintenance_color_scheme";

type ColorSchemeContextValue = {
  preference: ColorSchemePreference;
  setPreference: (value: ColorSchemePreference) => void;
  darkMode: boolean;
};

const ColorSchemeContext = createContext<ColorSchemeContextValue | null>(null);

function getStoredPreference(): ColorSchemePreference {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark" || stored === "system") {
    return stored;
  }
  return "light";
}

function getSystemDarkMode(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function ColorSchemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState<ColorSchemePreference>(getStoredPreference);
  const [systemDark, setSystemDark] = useState(getSystemDarkMode);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e: MediaQueryListEvent) => setSystemDark(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const darkMode = preference === "system" ? systemDark : preference === "dark";

  const setPreference = useCallback((value: ColorSchemePreference) => {
    localStorage.setItem(STORAGE_KEY, value);
    setPreferenceState(value);
  }, []);

  const value = useMemo(
    () => ({ preference, setPreference, darkMode }),
    [preference, setPreference, darkMode],
  );

  return <ColorSchemeContext.Provider value={value}>{children}</ColorSchemeContext.Provider>;
}

export function useColorScheme(): ColorSchemeContextValue {
  const ctx = useContext(ColorSchemeContext);
  if (!ctx) {
    throw new Error("useColorScheme must be used within ColorSchemeProvider");
  }
  return ctx;
}
