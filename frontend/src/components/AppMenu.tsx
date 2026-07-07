import AssessmentIcon from "@mui/icons-material/Assessment";
import BuildIcon from "@mui/icons-material/Build";
import DashboardIcon from "@mui/icons-material/Dashboard";
import DnsIcon from "@mui/icons-material/Dns";
import EventNoteIcon from "@mui/icons-material/EventNote";
import LogoutIcon from "@mui/icons-material/Logout";
import SettingsIcon from "@mui/icons-material/Settings";
import WarningIcon from "@mui/icons-material/Warning";
import HistoryIcon from "@mui/icons-material/History";
import ListAltIcon from "@mui/icons-material/ListAlt";
import {
  Badge,
  Box,
  Divider,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useLocation } from "react-router-dom";
import { api } from "../api/client";
import { useStrings } from "../hooks/useLocale";
import MenuItem from "./MenuItem";

type AppMenuProps = {
  userName?: string;
  onLogout?: () => void;
  onNavigate?: () => void;
};

function LowStockIcon() {
  const { data } = useQuery({
    queryKey: ["low-stock"],
    queryFn: api.getLowStock,
    refetchInterval: 120_000,
  });
  const count = data?.length ?? 0;
  if (count === 0) return <WarningIcon />;
  return (
    <Badge badgeContent={count} color="error">
      <WarningIcon />
    </Badge>
  );
}

export default function AppMenu({ userName, onLogout, onNavigate }: AppMenuProps) {
  const strings = useStrings();
  const location = useLocation();

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <List sx={{ flexGrow: 1 }}>
        <MenuItem
          title={strings.nav.dashboard}
          link="/"
          icon={<DashboardIcon />}
          selected={location.pathname === "/"}
          onNavigate={onNavigate}
        />
        <MenuItem
          title={strings.nav.vehicles}
          link="/vehicles"
          icon={<DnsIcon />}
          selected={
            location.pathname === "/vehicles" || location.pathname.startsWith("/vehicles/")
          }
          onNavigate={onNavigate}
        />
        <MenuItem
          title={strings.nav.reports}
          link="/reports"
          icon={<AssessmentIcon />}
          selected={location.pathname === "/reports"}
          onNavigate={onNavigate}
        />
        <MenuItem
          title={strings.nav.upcomingMaintenance}
          link="/maintenance"
          icon={<EventNoteIcon />}
          selected={location.pathname === "/maintenance"}
          onNavigate={onNavigate}
        />
        <MenuItem
          title={strings.nav.services}
          link="/services"
          icon={<HistoryIcon />}
          selected={location.pathname === "/services"}
          onNavigate={onNavigate}
        />
        <MenuItem
          title={strings.nav.serviceTypes}
          link="/service-types"
          icon={<ListAltIcon />}
          selected={location.pathname === "/service-types"}
          onNavigate={onNavigate}
        />
        <MenuItem
          title={strings.nav.parts}
          link="/parts"
          icon={<BuildIcon />}
          selected={location.pathname === "/parts"}
          onNavigate={onNavigate}
        />
        <MenuItem
          title={strings.nav.lowStock}
          link="/stock/low"
          icon={<LowStockIcon />}
          selected={location.pathname === "/stock/low"}
          onNavigate={onNavigate}
        />
        <Divider sx={{ my: 1 }} />
        <MenuItem
          title={strings.nav.settings}
          link="/settings"
          icon={<SettingsIcon />}
          selected={location.pathname === "/settings"}
          onNavigate={onNavigate}
        />
      </List>
      <Divider />
      <Box sx={{ p: 2 }}>
        {userName && (
          <Typography variant="body2" color="text.secondary" noWrap sx={{ mb: 1 }}>
            {userName}
          </Typography>
        )}
        {onLogout && (
          <ListItemButton onClick={onLogout}>
            <ListItemIcon>
              <LogoutIcon />
            </ListItemIcon>
            <ListItemText primary={strings.auth.signOut} />
          </ListItemButton>
        )}
      </Box>
    </Box>
  );
}
