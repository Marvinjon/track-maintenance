import { createTheme } from "@mui/material/styles";
import { components } from "./components";
import { dimensions } from "./dimensions";
import { createPalette } from "./palette";

declare module "@mui/material/styles" {
  interface Palette {
    neutral: Palette["primary"];
    geometry: Palette["primary"];
    alwaysDark: Palette["primary"];
  }
  interface PaletteOptions {
    neutral?: PaletteOptions["primary"];
    geometry?: PaletteOptions["primary"];
    alwaysDark?: PaletteOptions["primary"];
  }
  interface Theme {
    dimensions: typeof dimensions;
  }
  interface ThemeOptions {
    dimensions?: typeof dimensions;
  }
}

export function createTraccarTheme(darkMode: boolean) {
  return createTheme({
    typography: {
      fontFamily: "Roboto, Segoe UI, Helvetica Neue, Arial, sans-serif",
    },
    palette: createPalette(darkMode),
    dimensions,
    components,
  });
}
