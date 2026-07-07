import {
  Alert,
  Box,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { ReminderWithVehicle } from "../api/types";
import { ReminderBadge } from "../components/ReminderBadge";
import { TableExportButton } from "../components/TableExportButton";
import { TablePanel } from "../components/TablePanel";
import { remindersExportSheet } from "../export/datasets";
import { useSettingsStyles } from "../styles/useSettingsStyles";
import type { Strings } from "../i18n";
import { useStrings } from "../hooks/useLocale";

function vehicleDisplay(strings: Strings, reminder: ReminderWithVehicle): string {
  return (
    reminder.vehicle_plate?.trim() ||
    reminder.vehicle_device_name?.trim() ||
    strings.common.notAvailable
  );
}

function deviceSubtitle(reminder: ReminderWithVehicle): string | null {
  if (reminder.vehicle_plate && reminder.vehicle_device_name) {
    return reminder.vehicle_device_name;
  }
  return null;
}

export default function UpcomingMaintenancePage() {
  const strings = useStrings();
  const navigate = useNavigate();
  const { classes } = useSettingsStyles();
  const { data: reminders, isLoading, isError } = useQuery({
    queryKey: ["all-reminders"],
    queryFn: api.getAllReminders,
  });

  if (isLoading) return <Typography>{strings.common.loading}</Typography>;
  if (isError || !reminders) return <Alert severity="error">{strings.common.error}</Alert>;

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2, flexWrap: "wrap", gap: 1 }}>
        <Typography variant="h5">{strings.reminders.fleetTitle}</Typography>
        <TableExportButton
          filename="upcoming-maintenance"
          sheets={() => [remindersExportSheet(strings, reminders)]}
          disabled={reminders.length === 0}
        />
      </Box>
      {reminders.length === 0 ? (
        <Typography color="text.secondary">{strings.reminders.fleetEmpty}</Typography>
      ) : (
        <TablePanel>
          <Table className={classes.table} size="small">
            <TableHead>
              <TableRow>
                <TableCell>{strings.reminders.vehicle}</TableCell>
                <TableCell>{strings.reminders.serviceType}</TableCell>
                <TableCell className={classes.hideOnMobile}>{strings.reminders.intervalKm}</TableCell>
                <TableCell className={classes.hideOnMobile}>{strings.reminders.intervalDays}</TableCell>
                <TableCell className={classes.hideOnMobile}>{strings.reminders.lastService}</TableCell>
                <TableCell>{strings.reminders.status}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {reminders.map((reminder) => {
                const subtitle = deviceSubtitle(reminder);
                return (
                  <TableRow
                    key={reminder.id}
                    hover
                    sx={{ cursor: "pointer" }}
                    onClick={() => navigate(`/vehicles/${reminder.vehicle_id}`)}
                  >
                    <TableCell>
                      <Typography variant="body2">{vehicleDisplay(strings, reminder)}</Typography>
                      {subtitle && (
                        <Typography variant="caption" color="text.secondary">
                          {subtitle}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>{reminder.service_type_name}</TableCell>
                    <TableCell className={classes.hideOnMobile}>
                      {reminder.interval_km?.toLocaleString("en-GB") ??
                        strings.common.notAvailable}
                    </TableCell>
                    <TableCell className={classes.hideOnMobile}>
                      {reminder.interval_days ?? strings.common.notAvailable}
                    </TableCell>
                    <TableCell className={classes.hideOnMobile}>
                      {reminder.last_service_date ?? strings.common.never}
                      {reminder.last_service_odometer_km !== null && (
                        <Typography component="span" variant="caption" color="text.secondary">
                          {" "}
                          {strings.reminders.atKm(
                            Number(reminder.last_service_odometer_km).toLocaleString("en-GB", {
                              maximumFractionDigits: 1,
                            }),
                          )}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: "flex", gap: 0.5, alignItems: "center" }}>
                        <ReminderBadge status={reminder.status} />
                        {reminder.sync_error && (
                          <Tooltip title={strings.reminders.syncErrorHint}>
                            <Chip
                              label={strings.reminders.syncError}
                              color="warning"
                              size="small"
                              variant="outlined"
                            />
                          </Tooltip>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TablePanel>
      )}
    </>
  );
}
