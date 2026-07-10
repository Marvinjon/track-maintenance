import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Stack,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { DashboardRecord } from "../api/types";
import { NewServiceModal } from "../components/NewServiceModal";
import { RecordDrawer } from "../components/RecordDrawer";
import { formatCost } from "../format";
import type { Strings } from "../i18n";
import { useCurrency } from "../hooks/useCurrency";
import { isTraccarReadOnly, useAuthUser } from "../hooks/useAuthUser";
import { useStrings } from "../hooks/useLocale";

function vehicleDisplay(strings: Strings, record: DashboardRecord): string {
  return (
    record.vehicle_plate?.trim() ||
    record.vehicle_device_name?.trim() ||
    strings.common.notAvailable
  );
}

function StatCard({
  title,
  value,
  subtitle,
  color,
  to,
}: {
  title: string;
  value: string;
  subtitle?: string;
  color?: "error" | "warning" | "default";
  to?: string;
}) {
  const content = (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {title}
        </Typography>
        <Typography variant="h4" color={color === "error" ? "error" : undefined}>
          {value}
        </Typography>
        {subtitle && (
          <Typography variant="caption" color="text.secondary">
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
  if (to) {
    return (
      <Box component={Link} to={to} sx={{ textDecoration: "none", color: "inherit" }}>
        {content}
      </Box>
    );
  }
  return content;
}

export default function DashboardPage() {
  const strings = useStrings();
  const { currency: preferredCurrency } = useCurrency();
  const { data: authUser } = useAuthUser();
  const readOnly = isTraccarReadOnly(authUser);
  const [logServiceOpen, setLogServiceOpen] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<DashboardRecord | null>(null);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.getDashboard,
  });

  if (isLoading) return <Typography>{strings.common.loading}</Typography>;
  if (isError || !data) return <Alert severity="error">{strings.common.error}</Alert>;

  const currency = data.currency ?? preferredCurrency;
  const spendSubtitle = strings.dashboard.vsLastMonth(
    formatCost(String(data.spend_last_month), currency),
  );

  return (
    <>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5">{strings.dashboard.title}</Typography>
        <Button
          variant="contained"
          onClick={() => setLogServiceOpen(true)}
          disabled={readOnly}
          title={readOnly ? strings.logService.noTraccarPermission : undefined}
        >
          {strings.vehicleDetail.logService}
        </Button>
      </Stack>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "1fr 1fr",
            md: "repeat(4, 1fr)",
          },
          gap: 2,
          mb: 3,
        }}
      >
        <StatCard
          title={strings.dashboard.spendThisMonth}
          value={formatCost(String(data.spend_this_month), currency)}
          subtitle={spendSubtitle}
          to="/reports"
        />
        <StatCard
          title={strings.dashboard.overdueReminders}
          value={String(data.overdue_reminders)}
          color={data.overdue_reminders > 0 ? "error" : "default"}
          to="/maintenance"
        />
        <StatCard
          title={strings.dashboard.dueSoonReminders}
          value={String(data.due_soon_reminders)}
          color={data.due_soon_reminders > 0 ? "warning" : "default"}
          to="/maintenance"
        />
        <StatCard
          title={strings.dashboard.lowStock}
          value={String(data.low_stock_count)}
          color={data.low_stock_count > 0 ? "warning" : "default"}
          to="/stock/low"
        />
      </Box>

      <Typography variant="h6" gutterBottom>
        {strings.dashboard.recentServices}
      </Typography>
      {data.recent_records.length === 0 ? (
        <Typography color="text.secondary">{strings.services.empty}</Typography>
      ) : (
        <Stack spacing={1}>
          {data.recent_records.map((record) => (
            <Box
              key={record.id}
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                p: 1.5,
                border: 1,
                borderColor: "divider",
                borderRadius: 1,
                cursor: "pointer",
                "&:hover": { bgcolor: "action.hover" },
              }}
              onClick={() => setSelectedRecord(record)}
            >
              <Box>
                <Typography variant="body2">
                  {record.vehicle_plate || record.vehicle_device_name || strings.common.notAvailable}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {record.service_type_name} · {record.performed_at}
                </Typography>
              </Box>
              <Typography variant="body2">
                {formatCost(record.cost, record.currency)}
              </Typography>
            </Box>
          ))}
        </Stack>
      )}

      <NewServiceModal open={logServiceOpen} onClose={() => setLogServiceOpen(false)} />
      <RecordDrawer
        recordId={selectedRecord?.id ?? null}
        vehicleLabel={selectedRecord ? vehicleDisplay(strings, selectedRecord) : undefined}
        onClose={() => setSelectedRecord(null)}
      />
    </>
  );
}
