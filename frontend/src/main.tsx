import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { AppThemeProvider } from "./AppThemeProvider";
import { branding } from "./branding";
import { ConfirmProvider } from "./hooks/useConfirm";
import { LocaleProvider } from "./hooks/useLocale";

const favicon = document.querySelector<HTMLLinkElement>("link[rel='icon']");
if (favicon) {
  favicon.href = branding.faviconUrl;
} else {
  const link = document.createElement("link");
  link.rel = "icon";
  link.href = branding.faviconUrl;
  document.head.appendChild(link);
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <LocaleProvider>
        <AppThemeProvider>
          <ConfirmProvider>
            <App />
          </ConfirmProvider>
        </AppThemeProvider>
      </LocaleProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
