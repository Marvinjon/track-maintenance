/** Build-time branding overrides (see frontend/.env.branding.example). */
export const branding = {
  appTitle: import.meta.env.VITE_APP_TITLE?.trim() || "",
  logoUrl: import.meta.env.VITE_LOGO_URL?.trim() || "",
  logoAlt: import.meta.env.VITE_LOGO_ALT?.trim() || "Logo",
  faviconUrl: import.meta.env.VITE_FAVICON_URL?.trim() || "/favicon.svg",
  primaryColor: import.meta.env.VITE_PRIMARY_COLOR?.trim() || "",
};

export function resolveAppTitle(fallback: string): string {
  return branding.appTitle || fallback;
}
