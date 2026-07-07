import { makeStyles } from "tss-react/mui";

export const useSettingsStyles = makeStyles()((theme) => ({
  tableWrap: {
    marginBottom: theme.spacing(10),
    [theme.breakpoints.down("md")]: {
      overflowX: "auto",
      WebkitOverflowScrolling: "touch",
      marginBottom: theme.spacing(12),
    },
  },
  table: {
    marginBottom: 0,
  },
  columnAction: {
    width: "1%",
    paddingRight: theme.spacing(1),
  },
  hideOnMobile: {
    [theme.breakpoints.down("md")]: {
      display: "none",
    },
  },
  container: {
    marginTop: theme.spacing(2),
  },
  pageHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: theme.spacing(2),
    [theme.breakpoints.down("md")]: {
      flexDirection: "column",
      alignItems: "stretch",
      gap: theme.spacing(1.5),
    },
  },
  buttons: {
    marginTop: theme.spacing(2),
    marginBottom: theme.spacing(2),
    display: "flex",
    justifyContent: "space-evenly",
    "& > *": {
      flexBasis: "33%",
    },
    [theme.breakpoints.down("md")]: {
      flexDirection: "column-reverse",
      alignItems: "stretch",
      gap: theme.spacing(1),
      "& > *": {
        flexBasis: "auto",
        width: "100%",
      },
    },
  },
  details: {
    display: "flex",
    flexDirection: "column",
    gap: theme.spacing(2),
    paddingBottom: theme.spacing(3),
  },
  stackOnMobile: {
    display: "flex",
    gap: theme.spacing(2),
    [theme.breakpoints.down("md")]: {
      flexDirection: "column",
    },
  },
  verticalActions: {
    display: "flex",
    flexDirection: "column",
  },
  fab: {
    position: "fixed",
    bottom: `calc(${theme.spacing(2)} + env(safe-area-inset-bottom, 0px))`,
    right: `calc(${theme.spacing(2)} + env(safe-area-inset-right, 0px))`,
  },
}));
