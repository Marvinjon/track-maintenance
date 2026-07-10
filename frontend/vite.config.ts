import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/** Load optional frontend/.env.branding (see .env.branding.example). */
function loadBrandingEnvFile() {
  const file = resolve(__dirname, ".env.branding");
  if (!existsSync(file)) return;

  for (const line of readFileSync(file, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    const separator = trimmed.indexOf("=");
    if (separator === -1) continue;

    const key = trimmed.slice(0, separator).trim();
    let value = trimmed.slice(separator + 1).trim();

    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }

    process.env[key] = value;
  }
}

loadBrandingEnvFile();

function brandingHtmlPlugin() {
  return {
    name: "branding-html",
    transformIndexHtml(html: string) {
      const title = process.env.VITE_APP_TITLE?.trim();
      if (!title) return html;
      return html.replace(/<title>.*?<\/title>/, `<title>${title}</title>`);
    },
  };
}

export default defineConfig({
  base: process.env.VITE_BASE_PATH || "/",
  plugins: [brandingHtmlPlugin(), react()],
  server: {
    // Dev only: forward API calls to a locally running backend.
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
