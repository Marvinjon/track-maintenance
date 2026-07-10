import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  Box,
  Button,
  Divider,
  Drawer,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { MaintenanceRecordWithVehicle, ServiceType } from "../api/types";
import { fetchAllServiceTypeRecords, recordsExportSheet } from "../export/datasets";
import { formatCost, formatKm } from "../format";
import { useConfirm } from "../hooks/useConfirm";
import { isTraccarReadOnly, useAuthUser } from "../hooks/useAuthUser";
import { useSettingsStyles } from "../styles/useSettingsStyles";
import type { Strings } from "../i18n";
import { useStrings } from "../hooks/useLocale";
import { TableExportButton } from "./TableExportButton";
import { TablePanel } from "./TablePanel";

function vehicleDisplay(
  strings: Strings,
  plate: string | null | undefined,
  deviceName: string | null | undefined,
): string {
  return plate?.trim() || deviceName?.trim() || strings.common.notAvailable;
}

export function ServiceTypeDrawer({
  serviceType,
  onClose,
  onRecordClick,
}: {
  serviceType: ServiceType | null;
  onClose: () => void;
  onRecordClick?: (record: MaintenanceRecordWithVehicle) => void;
}) {
  const strings = useStrings();
  const confirm = useConfirm();
  const queryClient = useQueryClient();
  const { data: authUser } = useAuthUser();
  const readOnly = isTraccarReadOnly(authUser);
  const { classes } = useSettingsStyles();
  const open = serviceType !== null;
  const [limit, setLimit] = useState(20);

  const [name, setName] = useState("");
  const [intervalKm, setIntervalKm] = useState("");
  const [intervalDays, setIntervalDays] = useState("");

  useEffect(() => {
    if (!serviceType) return;
    setName(serviceType.name);
    setIntervalKm(
      serviceType.default_interval_km != null
        ? String(serviceType.default_interval_km)
        : "",
    );
    setIntervalDays(
      serviceType.default_interval_days != null
        ? String(serviceType.default_interval_days)
        : "",
    );
    setLimit(20);
  }, [serviceType]);

  const { data: history } = useQuery({
    queryKey: ["service-type-records", serviceType?.id, limit],
    queryFn: () => api.getServiceTypeRecords(serviceType!.id, limit, 0),
    enabled: open,
  });

  const updateMutation = useMutation({
    mutationFn: () =>
      api.updateServiceType(serviceType!.id, {
        name: name.trim(),
        default_interval_km: intervalKm === "" ? undefined : Number(intervalKm),
        default_interval_days: intervalDays === "" ? undefined : Number(intervalDays),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["service-types"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteServiceType(serviceType!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["service-types"] });
      onClose();
    },
  });

  const canSave =
    serviceType !== null &&
    name.trim() !== "" &&
    (name.trim() !== serviceType.name ||
      intervalKm !==
        (serviceType.default_interval_km != null
          ? String(serviceType.default_interval_km)
          : "") ||
      intervalDays !==
        (serviceType.default_interval_days != null
          ? String(serviceType.default_interval_days)
          : ""));

  return (
    <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: 520 } }}>
      <Box sx={{ p: 2, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Typography variant="h6">{serviceType?.name ?? ""}</Typography>
        <IconButton onClick={onClose} aria-label={strings.common.cancel}>
          <CloseIcon />
        </IconButton>
      </Box>
      <Divider />
      {serviceType && (
        <Box sx={{ p: 2 }}>
          <Stack spacing={2}>
            <Typography variant="subtitle2">{strings.serviceTypes.editDefaults}</Typography>
            <TextField
              label={strings.serviceTypes.name}
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              fullWidth
              size="small"
            />
            <Box className={classes.stackOnMobile}>
              <TextField
                label={strings.serviceTypes.defaultIntervalKm}
                type="number"
                value={intervalKm}
                onChange={(e) => setIntervalKm(e.target.value)}
                size="small"
                fullWidth
                inputProps={{ min: 1 }}
              />
              <TextField
                label={strings.serviceTypes.defaultIntervalDays}
                type="number"
                value={intervalDays}
                onChange={(e) => setIntervalDays(e.target.value)}
                size="small"
                fullWidth
                inputProps={{ min: 1 }}
              />
            </Box>
            <Button
              variant="contained"
              onClick={() => updateMutation.mutate()}
              disabled={!canSave || updateMutation.isPending}
              sx={{ alignSelf: "flex-start" }}
            >
              {strings.common.save}
            </Button>

            {!readOnly && (
              <Button
                variant="outlined"
                color="error"
                startIcon={<DeleteIcon />}
                disabled={deleteMutation.isPending}
                onClick={async () => {
                  if (await confirm(strings.serviceTypes.deleteConfirm)) {
                    deleteMutation.mutate();
                  }
                }}
                sx={{ alignSelf: "flex-start" }}
              >
                {strings.common.delete}
              </Button>
            )}

            <Divider />
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <Typography variant="subtitle2">{strings.serviceTypes.history}</Typography>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                {history && history.total > 0 && serviceType && (
                  <TableExportButton
                    filename={`service-type-${serviceType.id}-records`}
                    sheets={async () => [
                      recordsExportSheet(strings, await fetchAllServiceTypeRecords(serviceType.id)),
                    ]}
                  />
                )}
                {history && (
                  <Typography variant="caption" color="text.secondary">
                    {strings.serviceTypes.recordCount(history.total)}
                  </Typography>
                )}
              </Box>
            </Box>

            {history && history.items.length === 0 && (
              <Typography color="text.secondary">{strings.serviceTypes.historyEmpty}</Typography>
            )}
            {history && history.items.length > 0 && (
              <TablePanel>
                <Table size="small" className={classes.table}>
                  <TableHead>
                    <TableRow>
                      <TableCell>{strings.reminders.vehicle}</TableCell>
                      <TableCell>{strings.records.date}</TableCell>
                      <TableCell className={classes.hideOnMobile}>{strings.records.odometerKm}</TableCell>
                      <TableCell>{strings.records.cost}</TableCell>
                      <TableCell className={classes.hideOnMobile}>{strings.records.performedBy}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {history.items.map((record) => (
                      <TableRow
                        key={record.id}
                        hover={onRecordClick !== undefined}
                        sx={{ cursor: onRecordClick ? "pointer" : undefined }}
                        onClick={() => onRecordClick?.(record)}
                      >
                        <TableCell>
                          {vehicleDisplay(strings, record.vehicle_plate, record.vehicle_device_name)}
                        </TableCell>
                        <TableCell>{record.performed_at}</TableCell>
                        <TableCell className={classes.hideOnMobile}>
                          {formatKm(record.odometer_km)}
                        </TableCell>
                        <TableCell>{formatCost(record.cost, record.currency)}</TableCell>
                        <TableCell className={classes.hideOnMobile}>
                          {record.performed_by ?? strings.common.notAvailable}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TablePanel>
            )}
            {history && history.total > history.items.length && (
              <Button variant="text" onClick={() => setLimit((value) => value + 20)}>
                {strings.records.loadMore}
              </Button>
            )}
          </Stack>
        </Box>
      )}
    </Drawer>
  );
}
