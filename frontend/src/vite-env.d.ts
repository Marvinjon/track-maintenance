/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_TITLE?: string;
  readonly VITE_LOGIN_SUBTITLE?: string;
  readonly VITE_LOGO_URL?: string;
  readonly VITE_LOGO_ALT?: string;
  readonly VITE_FAVICON_URL?: string;
  readonly VITE_PRIMARY_COLOR?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
