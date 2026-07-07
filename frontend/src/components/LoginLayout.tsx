import { Box, Paper, useMediaQuery, useTheme } from "@mui/material";
import { makeStyles } from "tss-react/mui";
import AppLogo from "./AppLogo";

const useStyles = makeStyles()((theme) => ({
  root: {
    display: "flex",
    height: "100%",
  },
  sidebar: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    background: theme.palette.primary.main,
    paddingBottom: theme.spacing(5),
    width: theme.dimensions.sidebarWidth,
    [theme.breakpoints.down("lg")]: {
      width: theme.dimensions.sidebarWidthTablet,
    },
    [theme.breakpoints.down("sm")]: {
      width: "0px",
      display: "none",
    },
  },
  paper: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    flex: 1,
    boxShadow: "-2px 0px 16px rgba(0, 0, 0, 0.25)",
    [theme.breakpoints.up("lg")]: {
      padding: theme.spacing(0, 25, 0, 0),
    },
  },
  form: {
    maxWidth: theme.spacing(52),
    padding: theme.spacing(5),
    width: "100%",
  },
}));

type LoginLayoutProps = {
  children: React.ReactNode;
};

export default function LoginLayout({ children }: LoginLayoutProps) {
  const { classes } = useStyles();
  const theme = useTheme();
  const showSidebar = useMediaQuery(theme.breakpoints.up("lg"));

  return (
    <div className={classes.root}>
      {showSidebar && (
        <Box className={classes.sidebar}>
          <AppLogo variant="sidebar" />
        </Box>
      )}
      <Paper square elevation={0} className={classes.paper}>
        <div className={classes.form}>{children}</div>
      </Paper>
    </div>
  );
}
