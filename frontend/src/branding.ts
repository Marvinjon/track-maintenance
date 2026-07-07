/** Build-time branding overrides (see frontend/.env.branding.example). */
export const DEFAULT_PLATFORM_NAME = "Traccar";

export const FALLBACK_DEFAULT_CURRENCY = "USD";

export const branding = {
  appTitle: import.meta.env.VITE_APP_TITLE?.trim() || "",
  loginSubtitle: import.meta.env.VITE_LOGIN_SUBTITLE?.trim() || "",
  platformName: import.meta.env.VITE_PLATFORM_NAME?.trim() || "",
  defaultCurrency: import.meta.env.VITE_DEFAULT_CURRENCY?.trim() || "",
  logoUrl: import.meta.env.VITE_LOGO_URL?.trim() || "",
  logoAlt: import.meta.env.VITE_LOGO_ALT?.trim() || "Logo",
  faviconUrl: import.meta.env.VITE_FAVICON_URL?.trim() || "/favicon.svg",
  primaryColor: import.meta.env.VITE_PRIMARY_COLOR?.trim() || "",
};

export function resolveAppTitle(fallback: string): string {
  return branding.appTitle || fallback;
}

export function resolveLoginSubtitle(fallback: string): string {
  return branding.loginSubtitle || fallback;
}

export function resolvePlatformName(fallback = DEFAULT_PLATFORM_NAME): string {
  return branding.platformName || fallback;
}

export function normalizeCurrencyCode(value: string): string {
  return value.trim().toUpperCase().slice(0, 3);
}

export function resolveDefaultCurrency(fallback = FALLBACK_DEFAULT_CURRENCY): string {
  const configured = branding.defaultCurrency;
  if (!configured) return fallback;
  const code = normalizeCurrencyCode(configured);
  return code.length === 3 ? code : fallback;
}

function brandPlatformText(text: string, platformName: string): string {
  if (platformName === DEFAULT_PLATFORM_NAME) return text;
  return text.split(DEFAULT_PLATFORM_NAME).join(platformName);
}

/** Replace default platform name in all user-visible strings (including function results). */
export function applyPlatformBranding<T>(strings: T, platformName = resolvePlatformName()): T {
  if (platformName === DEFAULT_PLATFORM_NAME) return strings;

  function walk<U>(value: U): U {
    if (typeof value === "string") {
      return brandPlatformText(value, platformName) as U;
    }
    if (typeof value === "function") {
      return ((...args: unknown[]) => {
        const result = (value as (...args: unknown[]) => unknown)(...args);
        return typeof result === "string" ? brandPlatformText(result, platformName) : result;
      }) as U;
    }
    if (value && typeof value === "object") {
      const branded: Record<string, unknown> = {};
      for (const [key, nested] of Object.entries(value)) {
        branded[key] = walk(nested);
      }
      return branded as U;
    }
    return value;
  }

  return walk(strings);
}
