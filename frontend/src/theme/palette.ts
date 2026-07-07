import { green, grey, indigo } from "@mui/material/colors";
import { branding } from "../branding";

export function createPalette(darkMode: boolean) {
  const primaryMain =
    branding.primaryColor || (darkMode ? indigo[200] : indigo[900]);

  return {
    mode: darkMode ? ("dark" as const) : ("light" as const),
    background: {
      default: darkMode ? grey[900] : grey[50],
    },
    primary: {
      main: primaryMain,
    },
    secondary: {
      main: darkMode ? green[200] : green[800],
    },
    neutral: {
      main: grey[500],
    },
    geometry: {
      main: "#3bb2d0",
    },
    alwaysDark: {
      main: grey[900],
    },
  };
}
