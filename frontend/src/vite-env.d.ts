/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_TITLE?: string;
  readonly VITE_LOGIN_SUBTITLE?: string;
  readonly VITE_PLATFORM_NAME?: string;
  readonly VITE_DEFAULT_CURRENCY?: string;
  readonly VITE_LOGO_URL?: string;
  readonly VITE_LOGO_ALT?: string;
  readonly VITE_FAVICON_URL?: string;
  readonly VITE_PRIMARY_COLOR?: string;
  readonly VITE_DEMO_MODE?: string;
  readonly VITE_BASE_PATH?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
