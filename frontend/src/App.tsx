import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ApiError, api, fetchSession } from "./api/client";
import PageLayout from "./components/PageLayout";
import { useAppMenu } from "./components/useAppMenu";
import { CurrencyProvider } from "./hooks/useCurrency";
import { useStrings } from "./hooks/useLocale";
import DashboardPage from "./pages/DashboardPage";
import LowStockPage from "./pages/LowStockPage";
import LoginPage from "./pages/LoginPage";
import PartsPage from "./pages/PartsPage";
import ReportsPage from "./pages/ReportsPage";
import ServiceTypesPage from "./pages/ServiceTypesPage";
import ServicesPage from "./pages/ServicesPage";
import SettingsPage from "./pages/SettingsPage";
import UpcomingMaintenancePage from "./pages/UpcomingMaintenancePage";
import VehicleDetailPage from "./pages/VehicleDetailPage";
import VehiclesPage from "./pages/VehiclesPage";
import { CircularProgress, Stack, Typography } from "@mui/material";

function ShellRoutes({ onLogout }: { onLogout: () => void }) {
  const strings = useStrings();
  const menu = useAppMenu({ onLogout });

  return (
    <Routes>
      <Route
        path="/"
        element={
          <PageLayout menu={menu} breadcrumbs={[strings.nav.dashboard]}>
            <DashboardPage />
          </PageLayout>
        }
      />
      <Route
        path="/vehicles"
        element={
          <PageLayout menu={menu} breadcrumbs={[strings.nav.vehicles]}>
            <VehiclesPage />
          </PageLayout>
        }
      />
      <Route
        path="/vehicles/:vehicleId"
        element={
          <PageLayout menu={menu} breadcrumbs={[strings.nav.vehicles]}>
            <VehicleDetailPage />
          </PageLayout>
        }
      />
      <Route
        path="/reports"
        element={
          <PageLayout menu={menu} breadcrumbs={[strings.nav.reports]}>
            <ReportsPage />
          </PageLayout>
        }
      />
      <Route
        path="/maintenance"
        element={
          <PageLayout menu={menu} breadcrumbs={[strings.nav.upcomingMaintenance]}>
            <UpcomingMaintenancePage />
          </PageLayout>
        }
      />
      <Route
        path="/services"
        element={
          <PageLayout menu={menu} breadcrumbs={[strings.nav.services]}>
            <ServicesPage />
          </PageLayout>
        }
      />
      <Route
        path="/service-types"
        element={
          <PageLayout menu={menu} breadcrumbs={[strings.nav.serviceTypes]}>
            <ServiceTypesPage />
          </PageLayout>
        }
      />
      <Route
        path="/parts"
        element={
          <PageLayout menu={menu} breadcrumbs={[strings.nav.parts]}>
            <PartsPage />
          </PageLayout>
        }
      />
      <Route
        path="/stock/low"
        element={
          <PageLayout menu={menu} breadcrumbs={[strings.nav.lowStock]}>
            <LowStockPage />
          </PageLayout>
        }
      />
      <Route
        path="/settings"
        element={
          <PageLayout menu={menu} breadcrumbs={[strings.settings.title]}>
            <SettingsPage />
          </PageLayout>
        }
      />
    </Routes>
  );
}

function AuthenticatedApp() {
  const strings = useStrings();
  const queryClient = useQueryClient();
  const [loggedOut, setLoggedOut] = useState(false);
  const session = useQuery({
    queryKey: ["auth", "me"],
    queryFn: fetchSession,
    retry: false,
  });

  const handleLogout = useCallback(async () => {
    setLoggedOut(true);
    try {
      await api.logout();
    } finally {
      await queryClient.cancelQueries();
      queryClient.setQueryData(["auth", "me"], null);
      queryClient.removeQueries({
        predicate: (query) =>
          query.queryKey[0] !== "auth" || query.queryKey[1] !== "me",
      });
    }
  }, [queryClient]);

  if (session.isLoading && !loggedOut) {
    return (
      <Stack alignItems="center" justifyContent="center" sx={{ minHeight: "100vh" }}>
        <CircularProgress />
        <Typography color="text.secondary">{strings.auth.checkingSession}</Typography>
      </Stack>
    );
  }

  if (session.isError) {
    const detail =
      session.error instanceof ApiError ? session.error.message : strings.common.error;
    return (
      <Stack alignItems="center" justifyContent="center" spacing={1} sx={{ minHeight: "100vh", px: 2 }}>
        <Typography color="error">{detail}</Typography>
        {session.error instanceof ApiError && session.error.status === 502 ? (
          <Typography color="text.secondary" textAlign="center">
            {strings.health.traccarUnreachable}
          </Typography>
        ) : null}
      </Stack>
    );
  }

  if (loggedOut || !session.data) {
    return (
      <LoginPage
        onSuccess={() => {
          setLoggedOut(false);
          void queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
        }}
      />
    );
  }

  return (
    <CurrencyProvider userId={session.data.id}>
      <BrowserRouter>
        <ShellRoutes onLogout={() => void handleLogout()} />
      </BrowserRouter>
    </CurrencyProvider>
  );
}

export default function App() {
  return <AuthenticatedApp />;
}
