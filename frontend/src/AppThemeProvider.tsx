import CssBaseline from "@mui/material/CssBaseline";
import { ThemeProvider } from "@mui/material/styles";
import type { ReactNode } from "react";
import { ColorSchemeProvider, useColorScheme } from "./hooks/useColorScheme";
import { createTraccarTheme } from "./theme";

function ThemedApp({ children }: { children: ReactNode }) {
  const { darkMode } = useColorScheme();
  const theme = createTraccarTheme(darkMode);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  );
}

export function AppThemeProvider({ children }: { children: ReactNode }) {
  return (
    <ColorSchemeProvider>
      <ThemedApp>{children}</ThemedApp>
    </ColorSchemeProvider>
  );
}
