import {
  Alert,
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { Vehicle } from "../api/types";
import { ReminderBadge } from "../components/ReminderBadge";
import { TableExportButton } from "../components/TableExportButton";
import { TablePanel } from "../components/TablePanel";
import { vehiclesExportSheet } from "../export/datasets";
import { traccarDeviceUrl, useTraccarPublicUrl } from "../hooks/useTraccarUrl";
import { formatAgo, formatKm } from "../format";
import { useSettingsStyles } from "../styles/useSettingsStyles";
import { useStrings } from "../hooks/useLocale";

function OdometerCell({ vehicle }: { vehicle: Vehicle }) {
  const strings = useStrings();
  const ago = formatAgo(vehicle.odometer_synced_at, strings);
  const label = ago ? strings.vehicles.syncedAgo(ago) : strings.vehicles.neverSynced;
  return (
    <Tooltip title={label}>
      <Typography variant="body2">{formatKm(vehicle.odometer_km_cached)}</Typography>
    </Tooltip>
  );
}

function EnableTrackingButton({
  vehicle,
  createDefaultReminders,
}: {
  vehicle: Vehicle;
  createDefaultReminders: boolean;
}) {
  const strings = useStrings();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () =>
      api.createVehicle({
        traccar_device_id: vehicle.traccar_device_id,
        create_default_reminders: createDefaultReminders,
      }),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ["vehicles"] });
      if (created.id !== null) navigate(`/vehicles/${created.id}`);
    },
  });
  return (
    <Button
      size="small"
      variant="outlined"
      disabled={mutation.isPending}
      onClick={(event) => {
        event.stopPropagation();
        mutation.mutate();
      }}
    >
      {strings.vehicles.enableTracking}
    </Button>
  );
}

function TraccarLink({ deviceId }: { deviceId: number }) {
  const strings = useStrings();
  const publicUrl = useTraccarPublicUrl();
  if (!publicUrl) return null;
  return (
    <Button
      size="small"
      variant="text"
      endIcon={<OpenInNewIcon fontSize="small" />}
      href={traccarDeviceUrl(publicUrl, deviceId)}
      target="_blank"
      rel="noopener noreferrer"
      onClick={(e) => e.stopPropagation()}
    >
      {strings.vehicles.viewInTraccar}
    </Button>
  );
}

export default function VehiclesPage() {
  const strings = useStrings();
  const navigate = useNavigate();
  const { classes } = useSettingsStyles();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [createDefaultReminders, setCreateDefaultReminders] = useState(false);

  const { data: vehicles, isLoading, isError } = useQuery({
    queryKey: ["vehicles"],
    queryFn: api.getVehicles,
  });

  const untracked = useMemo(
    () => (vehicles ?? []).filter((v) => !v.registered),
    [vehicles],
  );

  const bulkMutation = useMutation({
    mutationFn: () =>
      api.bulkCreateVehicles({
        traccar_device_ids: [...selected],
        create_default_reminders: createDefaultReminders,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vehicles"] });
      setSelected(new Set());
    },
  });

  const toggle = (deviceId: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(deviceId)) next.delete(deviceId);
      else next.add(deviceId);
      return next;
    });
  };

  const selectAllUntracked = () => {
    setSelected(new Set(untracked.map((v) => v.traccar_device_id)));
  };

  if (isLoading) return <Typography>{strings.common.loading}</Typography>;
  if (isError || !vehicles) return <Alert severity="error">{strings.common.error}</Alert>;
  if (vehicles.length === 0) return <Typography>{strings.vehicles.empty}</Typography>;

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2, flexWrap: "wrap", gap: 1 }}>
        <Typography variant="h5">{strings.vehicles.title}</Typography>
        <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
          <TableExportButton
            filename="vehicles"
            sheets={() => [vehiclesExportSheet(strings, vehicles)]}
            disabled={vehicles.length === 0}
          />
          {untracked.length > 0 && (
            <>
            <FormControlLabel
              control={
                <Checkbox
                  checked={createDefaultReminders}
                  onChange={(e) => setCreateDefaultReminders(e.target.checked)}
                />
              }
              label={strings.vehicles.bulkEnableReminders}
            />
            <Button size="small" onClick={selectAllUntracked}>
              {strings.vehicles.selectAll}
            </Button>
            <Button
              variant="contained"
              size="small"
              disabled={selected.size === 0 || bulkMutation.isPending}
              onClick={() => bulkMutation.mutate()}
            >
              {strings.vehicles.bulkEnable} ({selected.size})
            </Button>
            </>
          )}
        </Box>
      </Box>
      <TablePanel>
        <Table className={classes.table} size="small">
          <TableHead>
            <TableRow>
              {untracked.length > 0 && <TableCell padding="checkbox" />}
              <TableCell>{strings.vehicles.plate}</TableCell>
              <TableCell className={classes.hideOnMobile}>{strings.vehicles.device}</TableCell>
              <TableCell className={classes.hideOnMobile}>{strings.vehicles.makeModel}</TableCell>
              <TableCell>{strings.vehicles.odometer}</TableCell>
              <TableCell>{strings.vehicles.reminderStatus}</TableCell>
              <TableCell>{strings.vehicles.lastService}</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {vehicles.map((vehicle) => (
              <TableRow
                key={vehicle.traccar_device_id}
                hover={vehicle.registered}
                sx={{ cursor: vehicle.registered ? "pointer" : "default" }}
                onClick={() => {
                  if (vehicle.registered && vehicle.id !== null) {
                    navigate(`/vehicles/${vehicle.id}`);
                  }
                }}
              >
                {untracked.length > 0 && (
                  <TableCell padding="checkbox">
                    {!vehicle.registered && (
                      <Checkbox
                        checked={selected.has(vehicle.traccar_device_id)}
                        onClick={(e) => e.stopPropagation()}
                        onChange={() => toggle(vehicle.traccar_device_id)}
                      />
                    )}
                  </TableCell>
                )}
                <TableCell>
                  {vehicle.registered
                    ? vehicle.plate || strings.common.notAvailable
                    : strings.vehicles.notRegistered}
                </TableCell>
                <TableCell className={classes.hideOnMobile}>
                  {vehicle.device_name ?? strings.common.notAvailable}
                </TableCell>
                <TableCell className={classes.hideOnMobile}>
                  {[vehicle.make, vehicle.model].filter(Boolean).join(" ") ||
                    strings.common.notAvailable}
                </TableCell>
                <TableCell>
                  {vehicle.registered ? (
                    <OdometerCell vehicle={vehicle} />
                  ) : (
                    strings.common.notAvailable
                  )}
                </TableCell>
                <TableCell>
                  {vehicle.registered ? (
                    <ReminderBadge status={vehicle.reminder_status} />
                  ) : (
                    strings.common.notAvailable
                  )}
                </TableCell>
                <TableCell>
                  {vehicle.last_service_date ?? strings.common.never}
                </TableCell>
                <TableCell onClick={(e) => e.stopPropagation()}>
                  {!vehicle.registered ? (
                    <EnableTrackingButton
                      vehicle={vehicle}
                      createDefaultReminders={createDefaultReminders}
                    />
                  ) : (
                    <TraccarLink deviceId={vehicle.traccar_device_id} />
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TablePanel>
    </>
  );
}
