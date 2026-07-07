import { cloneElement, isValidElement, useState } from "react";
import {
  AppBar,
  Box,
  Breadcrumbs,
  Divider,
  Drawer,
  IconButton,
  Toolbar,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { makeStyles } from "tss-react/mui";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import MenuIcon from "@mui/icons-material/Menu";
import { useNavigate } from "react-router-dom";
import AppLogo from "./AppLogo";

const useStyles = makeStyles<{ miniVariant: boolean }>()((theme, { miniVariant }) => ({
  root: {
    height: "100%",
    display: "flex",
    [theme.breakpoints.down("md")]: {
      flexDirection: "column",
    },
  },
  drawerPaper: {
    overflowX: "hidden",
    transition: theme.transitions.create("width", {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.enteringScreen,
    }),
    ...(miniVariant && {
      "& .MuiListItemButton-root": {
        minHeight: 48,
      },
      "& .MuiListItemText-root": {
        display: "none",
      },
      "& .MuiListItemIcon-root": {
        minWidth: 0,
        justifyContent: "center",
      },
    }),
    "@media print": {
      display: "none",
    },
  },
  mobileDrawer: {
    width: theme.dimensions.drawerWidthTablet,
    "@media print": {
      display: "none",
    },
  },
  mobileToolbar: {
    zIndex: 1,
    "@media print": {
      display: "none",
    },
  },
  content: {
    flexGrow: 1,
    minWidth: 0,
    alignItems: "stretch",
    display: "flex",
    flexDirection: "column",
    overflowY: "auto",
    padding: theme.spacing(2),
    [theme.breakpoints.down("md")]: {
      padding: theme.spacing(1.5, 1),
    },
  },
}));

type PageLayoutProps = {
  menu: React.ReactNode;
  breadcrumbs: string[];
  children: React.ReactNode;
};

function PageTitle({ breadcrumbs }: { breadcrumbs: string[] }) {
  const theme = useTheme();
  const desktop = useMediaQuery(theme.breakpoints.up("md"));

  if (desktop) {
    return (
      <Typography variant="h6" color="inherit" noWrap>
        {breadcrumbs[0]}
      </Typography>
    );
  }
  return (
    <Breadcrumbs>
      {breadcrumbs.slice(0, -1).map((breadcrumb) => (
        <Typography key={breadcrumb} color="inherit">
          {breadcrumb}
        </Typography>
      ))}
      <Typography color="textPrimary">{breadcrumbs[breadcrumbs.length - 1]}</Typography>
    </Breadcrumbs>
  );
}

export default function PageLayout({ menu, breadcrumbs, children }: PageLayoutProps) {
  const [miniVariant, setMiniVariant] = useState(false);
  const theme = useTheme();
  const navigate = useNavigate();
  const desktop = useMediaQuery(theme.breakpoints.up("md"));
  const [openDrawer, setOpenDrawer] = useState(false);
  const { classes } = useStyles({ miniVariant });

  const drawerWidth = miniVariant ? theme.spacing(7) : theme.dimensions.drawerWidthDesktop;

  const toggleDrawer = () => setMiniVariant(!miniVariant);
  const closeMobileDrawer = () => setOpenDrawer(false);
  const menuWithClose =
    isValidElement(menu) && !desktop
      ? cloneElement(menu as React.ReactElement<{ onNavigate?: () => void }>, {
          onNavigate: closeMobileDrawer,
        })
      : menu;

  return (
    <div className={classes.root}>
      {desktop ? (
        <Drawer
          variant="permanent"
          sx={{
            width: drawerWidth,
            flexShrink: 0,
            "& .MuiDrawer-paper": {
              width: drawerWidth,
              boxSizing: "border-box",
            },
          }}
          classes={{ paper: classes.drawerPaper }}
        >
          <Toolbar
            disableGutters={miniVariant}
            sx={{
              justifyContent: miniVariant ? "center" : "space-between",
              alignItems: "center",
              px: miniVariant ? 0 : 2,
              minHeight: { xs: 56, sm: 64 },
            }}
          >
            {!miniVariant && (
              <Box
                onClick={() => navigate("/")}
                sx={{ flex: 1, minWidth: 0, cursor: "pointer" }}
              >
                <AppLogo variant="compact" />
              </Box>
            )}
            <IconButton
              onClick={toggleDrawer}
              size="small"
              aria-label={miniVariant ? "Expand sidebar" : "Collapse sidebar"}
              sx={{ flexShrink: 0 }}
            >
              {miniVariant ? (
                theme.direction === "rtl" ? (
                  <ChevronLeftIcon />
                ) : (
                  <ChevronRightIcon />
                )
              ) : theme.direction === "rtl" ? (
                <ChevronRightIcon />
              ) : (
                <ChevronLeftIcon />
              )}
            </IconButton>
          </Toolbar>
          {!miniVariant && <Divider />}
          {menu}
        </Drawer>
      ) : (
        <Drawer
          variant="temporary"
          open={openDrawer}
          onClose={() => setOpenDrawer(false)}
          classes={{ paper: classes.mobileDrawer }}
        >
          {menuWithClose}
        </Drawer>
      )}
      {!desktop && (
        <AppBar className={classes.mobileToolbar} position="sticky" color="inherit" elevation={1}>
          <Toolbar sx={{ gap: 1 }}>
            <IconButton edge="start" onClick={() => setOpenDrawer(true)}>
              <MenuIcon />
            </IconButton>
            <Box sx={{ minWidth: 0, flex: 1, overflow: "hidden" }}>
              <PageTitle breadcrumbs={breadcrumbs} />
            </Box>
          </Toolbar>
        </AppBar>
      )}
      <main className={classes.content}>{children}</main>
    </div>
  );
}
