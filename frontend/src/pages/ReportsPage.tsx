import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import {
  Alert,
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "../api/client";
import type { MonthlyCostRow } from "../api/types";
import { CostReportDetailDrawer } from "../components/CostReportDetailDrawer";
import { ReportsExportButton } from "../components/ReportsExportButton";
import { TablePanel } from "../components/TablePanel";
import { costReportSummarySheet } from "../export/datasets";
import { downloadTableExport } from "../export/tableExport";
import { formatCost } from "../format";
import { useSettingsStyles } from "../styles/useSettingsStyles";
import { useCurrency } from "../hooks/useCurrency";
import { useLocale, useStrings } from "../hooks/useLocale";

function monthLabel(year: number, month: number): string {
  return new Date(year, month - 1, 1).toLocaleDateString("en-GB", {
    month: "long",
    year: "numeric",
  });
}

function defaultFromDate(): string {
  const d = new Date();
  d.setMonth(d.getMonth() - 5);
  d.setDate(1);
  return d.toISOString().slice(0, 10);
}

function defaultToDate(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function ReportsPage() {
  const strings = useStrings();
  const { currency: preferredCurrency } = useCurrency();
  const { locale } = useLocale();
  const { classes } = useSettingsStyles();
  const [fromDate, setFromDate] = useState(defaultFromDate);
  const [toDate, setToDate] = useState(defaultToDate);
  const [vehicleId, setVehicleId] = useState<string>("");
  const [detailSelection, setDetailSelection] = useState<Pick<
    MonthlyCostRow,
    "vehicle_id" | "year" | "month"
  > | null>(null);

  const { data: vehicles } = useQuery({
    queryKey: ["vehicles"],
    queryFn: api.getVehicles,
  });

  const registeredVehicles = useMemo(
    () => (vehicles ?? []).filter((v) => v.registered && v.id !== null),
    [vehicles],
  );

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["cost-report", fromDate, toDate, vehicleId],
    queryFn: () =>
      api.getCostReport(
        fromDate,
        toDate,
        vehicleId === "" ? undefined : Number(vehicleId),
      ),
    enabled: fromDate <= toDate,
  });

  const handleExportSummary = async (format: "csv" | "xlsx") => {
    if (!data || data.rows.length === 0) return;
    downloadTableExport(format, `cost-report-${fromDate}-${toDate}`, [
      costReportSummarySheet(strings, locale, data),
    ]);
  };

  const summary = data?.summaries[0];
  const currency = summary?.currency ?? preferredCurrency;

  return (
    <>
      <Typography variant="h5" gutterBottom>
        {strings.reports.title}
      </Typography>

      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={2}
        sx={{ mb: 3 }}
        alignItems={{ md: "flex-end" }}
      >
        <TextField
          label={strings.reports.fromDate}
          type="date"
          value={fromDate}
          onChange={(e) => setFromDate(e.target.value)}
          size="small"
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          label={strings.reports.toDate}
          type="date"
          value={toDate}
          onChange={(e) => setToDate(e.target.value)}
          size="small"
          InputLabelProps={{ shrink: true }}
        />
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>{strings.reports.vehicleFilter}</InputLabel>
          <Select
            label={strings.reports.vehicleFilter}
            value={vehicleId}
            onChange={(e) => setVehicleId(e.target.value)}
          >
            <MenuItem value="">{strings.reports.allVehicles}</MenuItem>
            {registeredVehicles.map((v) => (
              <MenuItem key={v.id!} value={String(v.id)}>
                {v.plate || v.device_name || `#${v.id}`}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button variant="contained" onClick={() => refetch()} disabled={isFetching}>
          {strings.reports.run}
        </Button>
        <ReportsExportButton
          fromDate={fromDate}
          toDate={toDate}
          vehicleId={vehicleId === "" ? undefined : Number(vehicleId)}
          onExportSummary={handleExportSummary}
          disabled={!data || data.rows.length === 0}
        />
      </Stack>

      {fromDate > toDate && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {strings.reports.invalidRange}
        </Alert>
      )}

      {isLoading && <Typography>{strings.common.loading}</Typography>}
      {isError && <Alert severity="error">{strings.common.error}</Alert>}

      {data && (
        <>
          {summary && (
            <Stack direction="row" spacing={3} sx={{ mb: 3 }} flexWrap="wrap">
              <Box>
                <Typography variant="body2" color="text.secondary">
                  {strings.reports.totalSpend}
                </Typography>
                <Typography variant="h5">
                  {formatCost(String(summary.total_cost), currency)}
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  {strings.reports.laborCost}
                </Typography>
                <Typography variant="h6">
                  {formatCost(String(summary.total_labor_cost), currency)}
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  {strings.reports.partsCost}
                </Typography>
                <Typography variant="h6">
                  {formatCost(String(summary.total_parts_cost), currency)}
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  {strings.reports.recordCount}
                </Typography>
                <Typography variant="h5">{summary.record_count}</Typography>
              </Box>
            </Stack>
          )}

          {data.rows.length === 0 ? (
            <Typography color="text.secondary">{strings.reports.empty}</Typography>
          ) : (
            <>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                {strings.reports.clickRowHint}
              </Typography>
              <TablePanel>
                <Table size="small" className={classes.table}>
                  <TableHead>
                    <TableRow>
                      <TableCell>{strings.reports.period}</TableCell>
                      <TableCell>{strings.reminders.vehicle}</TableCell>
                      <TableCell>{strings.reports.laborCost}</TableCell>
                      <TableCell>{strings.reports.partsCost}</TableCell>
                      <TableCell>{strings.reports.totalCost}</TableCell>
                      <TableCell className={classes.hideOnMobile}>
                        {strings.reports.costPerKm}
                      </TableCell>
                      <TableCell className={classes.hideOnMobile}>
                        {strings.reports.costPerHour}
                      </TableCell>
                      <TableCell className={classes.hideOnMobile}>
                        {strings.reports.records}
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data.rows.map((row) => (
                      <TableRow
                        key={`${row.vehicle_id}-${row.year}-${row.month}`}
                        hover
                        sx={{ cursor: "pointer" }}
                        onClick={() =>
                          setDetailSelection({
                            vehicle_id: row.vehicle_id,
                            year: row.year,
                            month: row.month,
                          })
                        }
                      >
                      <TableCell>{monthLabel(row.year, row.month)}</TableCell>
                      <TableCell>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                          {row.vehicle_plate || row.vehicle_device_name || strings.common.notAvailable}
                          {row.odometer_stale && (
                            <Tooltip title={strings.reports.staleOdometer}>
                              <WarningAmberIcon fontSize="small" color="warning" />
                            </Tooltip>
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>{formatCost(String(row.labor_cost), row.currency)}</TableCell>
                      <TableCell>{formatCost(String(row.parts_cost), row.currency)}</TableCell>
                      <TableCell>{formatCost(String(row.total_cost), row.currency)}</TableCell>
                      <TableCell className={classes.hideOnMobile}>
                        {row.cost_per_km != null
                          ? `${formatCost(String(row.cost_per_km), row.currency)}/km`
                          : strings.common.notAvailable}
                      </TableCell>
                      <TableCell className={classes.hideOnMobile}>
                        {row.cost_per_hour != null
                          ? `${formatCost(String(row.cost_per_hour), row.currency)}/h`
                          : strings.common.notAvailable}
                      </TableCell>
                      <TableCell className={classes.hideOnMobile}>{row.record_count}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TablePanel>
            </>
          )}
        </>
      )}

      <CostReportDetailDrawer
        selection={detailSelection}
        onClose={() => setDetailSelection(null)}
      />
    </>
  );
}
