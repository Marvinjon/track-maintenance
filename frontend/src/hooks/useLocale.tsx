import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { DEFAULT_LOCALE, getStrings, isLocale, type Locale, type Strings } from "../i18n";

const STORAGE_KEY = "track_maintenance_locale";

type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  strings: Strings;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

function getStoredLocale(): Locale {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && isLocale(stored)) {
    return stored;
  }
  return DEFAULT_LOCALE;
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(getStoredLocale);

  const setLocale = useCallback((value: Locale) => {
    localStorage.setItem(STORAGE_KEY, value);
    setLocaleState(value);
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const strings = useMemo(() => getStrings(locale), [locale]);

  const value = useMemo(
    () => ({ locale, setLocale, strings }),
    [locale, setLocale, strings],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const ctx = useContext(LocaleContext);
  if (!ctx) {
    throw new Error("useLocale must be used within LocaleProvider");
  }
  return ctx;
}

export function useStrings(): Strings {
  return useLocale().strings;
}
