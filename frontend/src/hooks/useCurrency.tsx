import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { normalizeCurrencyCode, resolveDefaultCurrency } from "../branding";

export const BUILTIN_CURRENCIES = ["USD", "EUR", "GBP"] as const;
export type BuiltinCurrency = (typeof BUILTIN_CURRENCIES)[number];
export const CUSTOM_CURRENCY_OPTION = "__custom__" as const;
export type CurrencySelection = BuiltinCurrency | typeof CUSTOM_CURRENCY_OPTION;

export const DEFAULT_CURRENCY = resolveDefaultCurrency();

const STORAGE_KEY = "track_maintenance_currency_by_user";

type UserCurrencySettings = {
  selection: CurrencySelection;
  customCode: string;
};

type CurrencyContextValue = {
  currency: string;
  selection: CurrencySelection;
  customCode: string;
  setSelection: (value: CurrencySelection) => void;
  setCustomCode: (value: string) => void;
};

const CurrencyContext = createContext<CurrencyContextValue | null>(null);

export { normalizeCurrencyCode };

function isBuiltinCurrency(code: string): code is BuiltinCurrency {
  return BUILTIN_CURRENCIES.includes(code as BuiltinCurrency);
}

function defaultSettings(): UserCurrencySettings {
  const code = resolveDefaultCurrency();
  if (isBuiltinCurrency(code)) {
    return { selection: code, customCode: "" };
  }
  return { selection: CUSTOM_CURRENCY_OPTION, customCode: code };
}

function readAllSettings(): Record<string, UserCurrencySettings> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, UserCurrencySettings>;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeAllSettings(settings: Record<string, UserCurrencySettings>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

function getStoredSettings(userId: number): UserCurrencySettings {
  const settings = readAllSettings()[String(userId)];
  if (!settings) return defaultSettings();
  const selection = settings.selection;
  if (selection === CUSTOM_CURRENCY_OPTION || isBuiltinCurrency(selection)) {
    return {
      selection,
      customCode: normalizeCurrencyCode(settings.customCode ?? ""),
    };
  }
  return defaultSettings();
}

export function resolveCurrency(settings: UserCurrencySettings): string {
  if (settings.selection === CUSTOM_CURRENCY_OPTION) {
    const custom = normalizeCurrencyCode(settings.customCode);
    return custom.length === 3 ? custom : resolveDefaultCurrency();
  }
  return settings.selection;
}

export function CurrencyProvider({
  userId,
  children,
}: {
  userId: number;
  children: ReactNode;
}) {
  const [settings, setSettingsState] = useState<UserCurrencySettings>(() =>
    getStoredSettings(userId),
  );

  const setSelection = useCallback(
    (selection: CurrencySelection) => {
      setSettingsState((current) => {
        const next = { ...current, selection };
        const all = readAllSettings();
        all[String(userId)] = next;
        writeAllSettings(all);
        return next;
      });
    },
    [userId],
  );

  const setCustomCode = useCallback(
    (value: string) => {
      setSettingsState((current) => {
        const next = { ...current, customCode: normalizeCurrencyCode(value) };
        const all = readAllSettings();
        all[String(userId)] = next;
        writeAllSettings(all);
        return next;
      });
    },
    [userId],
  );

  const currency = useMemo(() => resolveCurrency(settings), [settings]);

  const value = useMemo(
    () => ({
      currency,
      selection: settings.selection,
      customCode: settings.customCode,
      setSelection,
      setCustomCode,
    }),
    [currency, settings.customCode, settings.selection, setCustomCode, setSelection],
  );

  return <CurrencyContext.Provider value={value}>{children}</CurrencyContext.Provider>;
}

export function useCurrency(): CurrencyContextValue {
  const ctx = useContext(CurrencyContext);
  if (!ctx) {
    throw new Error("useCurrency must be used within CurrencyProvider");
  }
  return ctx;
}
