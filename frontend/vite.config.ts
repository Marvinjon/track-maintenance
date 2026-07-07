import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    // Dev only: forward API calls to a locally running backend.
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
