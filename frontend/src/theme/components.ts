import type { Components, Theme } from "@mui/material/styles";

export const components: Components<Theme> = {
  MuiUseMediaQuery: {
    defaultProps: {
      noSsr: true,
    },
  },
  MuiOutlinedInput: {
    styleOverrides: {
      root: ({ theme }) => ({
        backgroundColor: theme.palette.background.default,
      }),
    },
  },
  MuiButton: {
    styleOverrides: {
      sizeMedium: {
        height: "40px",
      },
    },
  },
  MuiFormControl: {
    defaultProps: {
      size: "small",
    },
  },
  MuiSnackbar: {
    defaultProps: {
      anchorOrigin: {
        vertical: "bottom",
        horizontal: "center",
      },
    },
  },
  MuiTooltip: {
    defaultProps: {
      enterDelay: 500,
      enterNextDelay: 500,
    },
  },
  MuiTableCell: {
    styleOverrides: {
      root: ({ theme }) => ({
        [theme.breakpoints.down("md")]: {
          padding: theme.spacing(1),
        },
        "@media print": {
          color: theme.palette.alwaysDark.main,
        },
      }),
    },
  },
  MuiDrawer: {
    styleOverrides: {
      paperAnchorRight: ({ theme }) => ({
        [theme.breakpoints.down("md")]: {
          width: "100%",
        },
      }),
    },
  },
  MuiDialog: {
    styleOverrides: {
      paper: ({ theme }) => ({
        [theme.breakpoints.down("md")]: {
          margin: theme.spacing(1),
          width: `calc(100% - ${theme.spacing(2)})`,
          maxWidth: "none",
        },
      }),
    },
  },
};
