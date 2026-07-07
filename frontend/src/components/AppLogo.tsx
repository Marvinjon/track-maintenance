import { Box, Typography } from "@mui/material";
import { makeStyles } from "tss-react/mui";
import { branding, resolveAppTitle } from "../branding";
import { useStrings } from "../hooks/useLocale";

const useStyles = makeStyles<{ variant: "sidebar" | "compact" }>()((theme, { variant }) => ({
  root: {
    display: "flex",
    alignItems: "center",
    justifyContent: variant === "sidebar" ? "center" : "flex-start",
    color: variant === "sidebar" ? theme.palette.common.white : theme.palette.text.primary,
    padding: variant === "sidebar" ? theme.spacing(2) : 0,
    minWidth: 0,
  },
  image: {
    maxWidth: variant === "sidebar" ? "80%" : 140,
    maxHeight: variant === "sidebar" ? 48 : 32,
    objectFit: "contain",
  },
  title: {
    fontWeight: 500,
    textAlign: variant === "sidebar" ? "center" : "left",
  },
}));

type AppLogoProps = {
  variant?: "sidebar" | "compact";
};

export default function AppLogo({ variant = "sidebar" }: AppLogoProps) {
  const strings = useStrings();
  const { classes } = useStyles({ variant });
  const title = resolveAppTitle(strings.appTitle);

  if (branding.logoUrl) {
    return (
      <Box className={classes.root}>
        <img src={branding.logoUrl} alt={branding.logoAlt} className={classes.image} />
      </Box>
    );
  }

  return (
    <Box className={classes.root}>
      <Typography
        variant={variant === "sidebar" ? "h5" : "h6"}
        className={classes.title}
        noWrap
      >
        {title}
      </Typography>
    </Box>
  );
}
