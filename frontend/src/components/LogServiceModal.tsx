import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { PartsPicker, validPartRows, type PartRow } from "./PartsPicker";
import { todayIso } from "../format";
import { useSettingsStyles } from "../styles/useSettingsStyles";
import { useCurrency } from "../hooks/useCurrency";
import { useStrings } from "../hooks/useLocale";

interface LogServiceVehicle {
  id: number;
  odometer_km_cached: string | null;
}

interface Props {
  vehicle: LogServiceVehicle;
  open: boolean;
  onClose: () => void;
}

export function LogServiceModal({ vehicle, open, onClose }: Props) {
  const strings = useStrings();
  const { currency } = useCurrency();
  const queryClient = useQueryClient();
  const { classes } = useSettingsStyles();
  const { data: serviceTypes } = useQuery({
    queryKey: ["log-service-types", vehicle.id],
    queryFn: () => api.getLogServiceTypes(vehicle.id),
    enabled: open,
  });
  const { data: reminders } = useQuery({
    queryKey: ["reminders", vehicle.id],
    queryFn: () => api.getReminders(vehicle.id),
    enabled: open,
  });
  const { data: parts } = useQuery({
    queryKey: ["parts"],
    queryFn: () => api.getParts(),
    enabled: open,
  });

  const [serviceTypeId, setServiceTypeId] = useState("");
  const [performedAt, setPerformedAt] = useState(todayIso());
  const [odometerKm, setOdometerKm] = useState(
    vehicle.odometer_km_cached !== null ? String(Number(vehicle.odometer_km_cached)) : "",
  );
  const [odometerTouched, setOdometerTouched] = useState(false);
  const [cost, setCost] = useState("");
  const [performedBy, setPerformedBy] = useState("");
  const [notes, setNotes] = useState("");
  const [partRows, setPartRows] = useState<PartRow[]>([]);
  const [syncWarning, setSyncWarning] = useState<string | null>(null);

  const odometerSyncQuery = useQuery({
    queryKey: ["log-service-odometer-sync", vehicle.id],
    queryFn: () => api.syncOdometer(vehicle.id),
    enabled: open,
    retry: false,
    staleTime: 0,
  });

  useEffect(() => {
    if (open) {
      setOdometerTouched(false);
      setOdometerKm(
        vehicle.odometer_km_cached !== null
          ? String(Number(vehicle.odometer_km_cached))
          : "",
      );
      setServiceTypeId("");
      setSyncWarning(null);
    }
  }, [open, vehicle.id, vehicle.odometer_km_cached]);

  useEffect(() => {
    if (!open || odometerTouched) return;
    const synced = odometerSyncQuery.data?.odometer_km_cached;
    if (synced === null || synced === undefined) return;
    setOdometerKm(String(Number(synced)));
  }, [open, odometerTouched, odometerSyncQuery.data]);

  useEffect(() => {
    if (!odometerSyncQuery.data) return;
    queryClient.invalidateQueries({ queryKey: ["vehicle", vehicle.id] });
    queryClient.invalidateQueries({ queryKey: ["vehicles"] });
    queryClient.invalidateQueries({ queryKey: ["all-reminders"] });
    queryClient.invalidateQueries({ queryKey: ["reminders", vehicle.id] });
  }, [odometerSyncQuery.data, queryClient, vehicle.id]);

  const validParts = validPartRows(partRows);

  const estimatedPartsCost = validParts.reduce((sum, row) => {
    const part = (parts ?? []).find((p) => String(p.id) === row.partId);
    if (!part?.unit_cost) return sum;
    return sum + Number(part.unit_cost) * Number(row.quantity);
  }, 0);

  const laborCost = cost === "" ? 0 : Number(cost);

  const mutation = useMutation({
    mutationFn: () =>
      api.createRecord(vehicle.id!, {
        service_type_id: Number(serviceTypeId),
        performed_at: performedAt,
        odometer_km: odometerKm === "" ? undefined : odometerKm,
        cost: cost === "" ? undefined : cost,
        currency,
        performed_by: performedBy || undefined,
        notes: notes || undefined,
        parts: validParts.map((row) => ({
          part_id: Number(row.partId),
          quantity: row.quantity,
        })),
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["records", vehicle.id] });
      queryClient.invalidateQueries({ queryKey: ["all-records"] });
      queryClient.invalidateQueries({ queryKey: ["vehicle", vehicle.id] });
      queryClient.invalidateQueries({ queryKey: ["vehicles"] });
      queryClient.invalidateQueries({ queryKey: ["all-reminders"] });
      queryClient.invalidateQueries({ queryKey: ["reminders", vehicle.id] });
      queryClient.invalidateQueries({ queryKey: ["parts"] });
      queryClient.invalidateQueries({ queryKey: ["low-stock"] });
      if (data.traccar_sync_warning_code === "no_traccar_permission") {
        setSyncWarning(strings.logService.noTraccarPermission);
        return;
      }
      setServiceTypeId("");
      setCost("");
      setPerformedBy("");
      setNotes("");
      setPartRows([]);
      onClose();
    },
  });

  const selectedResetsTraccar = (reminders ?? []).some(
    (r) => r.service_type_id === Number(serviceTypeId) && r.traccar_maintenance_id !== null,
  );

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{strings.logService.title}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {syncWarning && (
            <Alert severity="warning" onClose={() => setSyncWarning(null)}>
              {syncWarning}
            </Alert>
          )}
          <FormControl fullWidth size="small" required>
            <InputLabel>{strings.records.serviceType}</InputLabel>
            <Select
              label={strings.records.serviceType}
              value={serviceTypeId}
              onChange={(e) => setServiceTypeId(e.target.value)}
            >
              {(serviceTypes ?? []).map((t) => (
                <MenuItem key={t.id} value={String(t.id)}>
                  {t.display_name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {selectedResetsTraccar && (
            <Typography variant="body2" color="text.secondary">
              {strings.logService.traccarResetHint}
            </Typography>
          )}
          <TextField
            label={strings.records.date}
            type="date"
            value={performedAt}
            onChange={(e) => setPerformedAt(e.target.value)}
            required
            fullWidth
            size="small"
            InputLabelProps={{ shrink: true }}
          />
          <TextField
            label={strings.records.odometerKm}
            type="number"
            value={odometerKm}
            onChange={(e) => {
              setOdometerTouched(true);
              setOdometerKm(e.target.value);
            }}
            fullWidth
            size="small"
            inputProps={{ min: 0, step: 0.1 }}
            helperText={
              odometerSyncQuery.isFetching
                ? strings.logService.syncingOdometer
                : odometerSyncQuery.isError
                  ? strings.logService.syncOdometerFailed
                  : undefined
            }
          />
          <TextField
            label={strings.records.cost}
            type="number"
            value={cost}
            onChange={(e) => setCost(e.target.value)}
            fullWidth
            size="small"
            inputProps={{ min: 0 }}
            InputProps={{ endAdornment: ` ${currency}` }}
          />
          <TextField
            label={strings.records.performedBy}
            value={performedBy}
            onChange={(e) => setPerformedBy(e.target.value)}
            fullWidth
            size="small"
          />
          <TextField
            label={strings.records.notes}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            multiline
            minRows={2}
            fullWidth
            size="small"
          />
          <PartsPicker
            rows={partRows}
            setRows={setPartRows}
            parts={parts ?? []}
            currency={currency}
          />
          {estimatedPartsCost > 0 && (
            <Typography variant="body2" color="text.secondary">
              {strings.logService.estimatedPartsCost}:{" "}
              {estimatedPartsCost.toLocaleString("en-GB")} {currency}
              {laborCost > 0 &&
                ` · ${strings.logService.totalWithParts(
                  `${estimatedPartsCost.toLocaleString("en-GB")} ${currency}`,
                  `${laborCost.toLocaleString("en-GB")} ${currency}`,
                )}`}
            </Typography>
          )}
        </Stack>
      </DialogContent>
      <DialogActions className={classes.buttons}>
        <Button variant="outlined" onClick={onClose}>
          {strings.common.cancel}
        </Button>
        <Button
          variant="contained"
          onClick={() => {
            if (syncWarning) {
              setSyncWarning(null);
              setServiceTypeId("");
              setCost("");
              setPerformedBy("");
              setNotes("");
              setPartRows([]);
              onClose();
              return;
            }
            mutation.mutate();
          }}
          disabled={mutation.isPending || (!syncWarning && (!serviceTypeId || !performedAt))}
        >
          {syncWarning ? strings.logService.dismiss : strings.logService.submit}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
