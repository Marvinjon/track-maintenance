import DeleteIcon from "@mui/icons-material/Delete";
import {
  Alert,
  Box,
  Button,
  Chip,
  FormControl,
  IconButton,
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
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import type { VehicleDetail } from "../api/types";
import { vehicleRemindersExportSheet } from "../export/datasets";
import { useSettingsStyles } from "../styles/useSettingsStyles";
import { ReminderBadge } from "./ReminderBadge";
import { TableExportButton } from "./TableExportButton";
import { TablePanel } from "./TablePanel";
import { useStrings } from "../hooks/useLocale";
import { useConfirm } from "../hooks/useConfirm";

function CreateReminderForm({ vehicle }: { vehicle: VehicleDetail }) {
  const strings = useStrings();
  const queryClient = useQueryClient();
  const traccarServiceTypeIds = new Set(
    vehicle.reminders
      .filter((r) => r.traccar_maintenance_id !== null)
      .map((r) => r.service_type_id),
  );
  const { data: serviceTypes } = useQuery({
    queryKey: ["service-types"],
    queryFn: api.getServiceTypes,
  });

  const [serviceTypeId, setServiceTypeId] = useState("");
  const [intervalKm, setIntervalKm] = useState("");
  const [intervalDays, setIntervalDays] = useState("");
  const [intervalHours, setIntervalHours] = useState("");

  const selectType = (value: string) => {
    setServiceTypeId(value);
    const type = serviceTypes?.find((t) => String(t.id) === value);
    if (type) {
      setIntervalKm(type.default_interval_km != null ? String(type.default_interval_km) : "");
      setIntervalDays(type.default_interval_days != null ? String(type.default_interval_days) : "");
    }
  };

  const mutation = useMutation({
    mutationFn: () =>
      api.createReminder(vehicle.id!, {
        service_type_id: Number(serviceTypeId),
        interval_km: intervalKm === "" ? undefined : Number(intervalKm),
        interval_days: intervalDays === "" ? undefined : Number(intervalDays),
        interval_hours: intervalHours === "" ? undefined : Number(intervalHours),
        last_service_odometer_km: vehicle.odometer_km_cached ?? undefined,
        last_service_engine_hours: vehicle.engine_hours_cached ?? undefined,
        last_service_date: vehicle.last_service_date ?? undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reminders", vehicle.id] });
      queryClient.invalidateQueries({ queryKey: ["vehicle", vehicle.id] });
      queryClient.invalidateQueries({ queryKey: ["vehicles"] });
      setServiceTypeId("");
      setIntervalKm("");
      setIntervalDays("");
      setIntervalHours("");
    },
  });

  return (
    <Stack spacing={1}>
      <Typography variant="subtitle2">{strings.reminders.newTitle}</Typography>
      <Typography variant="body2" color="text.secondary">
        {strings.reminders.localOnlyHint}
      </Typography>
      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", alignItems: "flex-end" }}>
        <FormControl size="small" sx={{ minWidth: 220 }}>
          <InputLabel>{strings.reminders.serviceType}</InputLabel>
          <Select
            label={strings.reminders.serviceType}
            value={serviceTypeId}
            onChange={(e) => selectType(e.target.value)}
          >
            {(serviceTypes ?? [])
              .filter((t) => !traccarServiceTypeIds.has(t.id))
              .map((t) => (
              <MenuItem key={t.id} value={String(t.id)}>
                {t.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <TextField
          label={strings.reminders.intervalKm}
          type="number"
          value={intervalKm}
          onChange={(e) => setIntervalKm(e.target.value)}
          size="small"
          sx={{ width: 140 }}
          inputProps={{ min: 1 }}
        />
        <TextField
          label={strings.reminders.intervalDays}
          type="number"
          value={intervalDays}
          onChange={(e) => setIntervalDays(e.target.value)}
          size="small"
          sx={{ width: 140 }}
          inputProps={{ min: 1 }}
        />
        <TextField
          label={strings.reminders.intervalHours}
          type="number"
          value={intervalHours}
          onChange={(e) => setIntervalHours(e.target.value)}
          size="small"
          sx={{ width: 140 }}
          inputProps={{ min: 1 }}
        />
        <Button
          variant="contained"
          onClick={() => mutation.mutate()}
          disabled={
            mutation.isPending ||
            !serviceTypeId ||
            (intervalKm === "" && intervalDays === "" && intervalHours === "")
          }
        >
          {strings.reminders.create}
        </Button>
      </Box>
    </Stack>
  );
}

export function RemindersTab({ vehicle }: { vehicle: VehicleDetail }) {
  const strings = useStrings();
  const confirm = useConfirm();
  const queryClient = useQueryClient();
  const { classes } = useSettingsStyles();
  const { data: reminders, isLoading } = useQuery({
    queryKey: ["reminders", vehicle.id],
    queryFn: () => api.getReminders(vehicle.id!),
  });

  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const syncMutation = useMutation({
    mutationFn: () => api.syncMaintenance(vehicle.id!),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["reminders", vehicle.id] });
      queryClient.invalidateQueries({ queryKey: ["vehicle", vehicle.id] });
      queryClient.invalidateQueries({ queryKey: ["vehicles"] });
      setSyncMessage(strings.reminders.syncSuccess(result.created, result.updated));
    },
    onError: () => setSyncMessage(strings.common.error),
  });

  const deleteMutation = useMutation({
    mutationFn: (reminderId: number) => api.deleteReminder(reminderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reminders", vehicle.id] });
      queryClient.invalidateQueries({ queryKey: ["vehicle", vehicle.id] });
      queryClient.invalidateQueries({ queryKey: ["vehicles"] });
    },
  });

  const isTraccarLinked = (reminder: { traccar_maintenance_id: number | null }) =>
    reminder.traccar_maintenance_id !== null;

  return (
    <Stack spacing={2} sx={{ mt: 2 }}>
      {syncMessage && (
        <Alert severity="info" onClose={() => setSyncMessage(null)}>
          {syncMessage}
        </Alert>
      )}
      {!vehicle.archived && (
        <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
          <Button
            variant="outlined"
            size="small"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
          >
            {syncMutation.isPending
              ? strings.reminders.syncingFromTraccar
              : strings.reminders.syncFromTraccar}
          </Button>
        </Box>
      )}

      {!vehicle.archived && <CreateReminderForm vehicle={vehicle} />}

      {isLoading && <Typography>{strings.common.loading}</Typography>}
      {reminders && reminders.length === 0 && (
        <Typography color="text.secondary">{strings.reminders.empty}</Typography>
      )}
      {reminders && reminders.length > 0 && (
        <>
          <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
            <TableExportButton
              filename={`vehicle-${vehicle.id}-reminders`}
              sheets={() => [vehicleRemindersExportSheet(strings, reminders)]}
            />
          </Box>
          <TablePanel>
          <Table size="small" className={classes.table}>
            <TableHead>
              <TableRow>
                <TableCell>{strings.reminders.serviceType}</TableCell>
                <TableCell className={classes.hideOnMobile}>{strings.reminders.intervalKm}</TableCell>
                <TableCell className={classes.hideOnMobile}>{strings.reminders.intervalDays}</TableCell>
                <TableCell className={classes.hideOnMobile}>{strings.reminders.intervalHours}</TableCell>
                <TableCell className={classes.hideOnMobile}>{strings.reminders.lastService}</TableCell>
                <TableCell>{strings.reminders.status}</TableCell>
                <TableCell className={classes.columnAction} />
              </TableRow>
            </TableHead>
            <TableBody>
              {reminders.map((reminder) => (
                <TableRow key={reminder.id}>
                  <TableCell>
                    <Box sx={{ display: "flex", gap: 0.5, alignItems: "center", flexWrap: "wrap" }}>
                      {reminder.service_type_name}
                      {isTraccarLinked(reminder) && (
                        <Chip
                          label={strings.reminders.fromTraccar}
                          size="small"
                          variant="outlined"
                        />
                      )}
                    </Box>
                  </TableCell>
                  <TableCell className={classes.hideOnMobile}>
                    {reminder.interval_km?.toLocaleString("en-GB") ??
                      strings.common.notAvailable}
                  </TableCell>
                  <TableCell className={classes.hideOnMobile}>
                    {reminder.interval_days ?? strings.common.notAvailable}
                  </TableCell>
                  <TableCell className={classes.hideOnMobile}>
                    {reminder.interval_hours ?? strings.common.notAvailable}
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
                  <TableCell className={classes.columnAction}>
                    {!vehicle.archived && !isTraccarLinked(reminder) && (
                      <IconButton
                        size="small"
                        color="error"
                        aria-label={strings.common.delete}
                        disabled={deleteMutation.isPending}
                        onClick={async () => {
                          if (await confirm(strings.reminders.deleteConfirmLocal)) {
                            deleteMutation.mutate(reminder.id);
                          }
                        }}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TablePanel>
        </>
      )}
    </Stack>
  );
}
