import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  Box,
  Button,
  Divider,
  Drawer,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { RecordChange } from "../api/types";
import { formatAgo, formatCost, formatKm } from "../format";
import type { Strings } from "../i18n";
import { useStrings } from "../hooks/useLocale";
import { useConfirm } from "../hooks/useConfirm";
import { PartsPicker, validPartRows, type PartRow } from "./PartsPicker";

interface Props {
  recordId: number | null;
  vehicleLabel?: string;
  onClose: () => void;
}

function formatChangeValue(
  strings: Strings,
  field: string,
  value: string | null,
  currency: string,
): string {
  if (value === null || value === "") return strings.common.notAvailable;
  if (field === "cost") return formatCost(value, currency);
  if (field === "odometer_km") return formatKm(value);
  return value;
}

function describeChange(strings: Strings, change: RecordChange, currency: string): string {
  const field =
    strings.records.fieldLabels[
      change.field as keyof typeof strings.records.fieldLabels
    ] ?? change.field;
  const oldValue = formatChangeValue(strings, change.field, change.old_value, currency);
  const newValue = formatChangeValue(strings, change.field, change.new_value, currency);

  if (change.old_value && change.new_value) {
    return strings.records.fieldChanged(field, oldValue, newValue);
  }
  if (!change.old_value && change.new_value) {
    return strings.records.fieldSet(field, newValue);
  }
  if (change.old_value && !change.new_value) {
    return strings.records.fieldCleared(field, oldValue);
  }
  return strings.records.fieldChanged(field, oldValue, newValue);
}

export function RecordDrawer({ recordId, vehicleLabel, onClose }: Props) {
  const strings = useStrings();
  const confirm = useConfirm();
  const queryClient = useQueryClient();
  const open = recordId !== null;

  const { data: record, isLoading } = useQuery({
    queryKey: ["record", recordId],
    queryFn: () => api.getRecord(recordId!),
    enabled: open,
  });
  const { data: serviceTypes } = useQuery({
    queryKey: ["service-types"],
    queryFn: api.getServiceTypes,
    enabled: open,
  });
  const { data: parts } = useQuery({
    queryKey: ["parts"],
    queryFn: () => api.getParts(),
    enabled: open,
  });

  const [serviceTypeId, setServiceTypeId] = useState("");
  const [performedAt, setPerformedAt] = useState("");
  const [odometerKm, setOdometerKm] = useState("");
  const [cost, setCost] = useState("");
  const [performedBy, setPerformedBy] = useState("");
  const [notes, setNotes] = useState("");
  const [partRows, setPartRows] = useState<PartRow[]>([]);

  useEffect(() => {
    if (!record) return;
    setServiceTypeId(String(record.service_type_id));
    setPerformedAt(record.performed_at);
    setOdometerKm(
      record.odometer_km !== null ? String(Number(record.odometer_km)) : "",
    );
    setCost(record.cost !== null ? String(Number(record.cost)) : "");
    setPerformedBy(record.performed_by ?? "");
    setNotes(record.notes ?? "");
    setPartRows(
      record.parts.map((part) => ({
        partId: String(part.part_id),
        quantity: String(Number(part.quantity)),
      })),
    );
  }, [record]);

  const stockBonus = useMemo(() => {
    if (!record) return {};
    return record.parts.reduce<Record<string, number>>((bonus, part) => {
      const key = String(part.part_id);
      bonus[key] = (bonus[key] ?? 0) + Number(part.quantity);
      return bonus;
    }, {});
  }, [record]);

  const invalidate = () => {
    if (recordId === null) return;
    queryClient.invalidateQueries({ queryKey: ["record", recordId] });
    queryClient.invalidateQueries({ queryKey: ["all-records"] });
    if (record) {
      queryClient.invalidateQueries({ queryKey: ["records", record.vehicle_id] });
      queryClient.invalidateQueries({ queryKey: ["vehicle", record.vehicle_id] });
      queryClient.invalidateQueries({ queryKey: ["service-type-records"] });
    }
    queryClient.invalidateQueries({ queryKey: ["vehicles"] });
    queryClient.invalidateQueries({ queryKey: ["all-reminders"] });
    queryClient.invalidateQueries({ queryKey: ["parts"] });
    queryClient.invalidateQueries({ queryKey: ["low-stock"] });
    queryClient.invalidateQueries({ queryKey: ["cost-report"] });
  };

  const validParts = validPartRows(partRows);

  const updateMutation = useMutation({
    mutationFn: () =>
      api.updateRecord(recordId!, {
        service_type_id: Number(serviceTypeId),
        performed_at: performedAt,
        odometer_km: odometerKm === "" ? undefined : odometerKm,
        cost: cost === "" ? undefined : cost,
        performed_by: performedBy || undefined,
        notes: notes || undefined,
        parts: validParts.map((row) => ({
          part_id: Number(row.partId),
          quantity: row.quantity,
        })),
      }),
    onSuccess: () => invalidate(),
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteRecord(recordId!),
    onSuccess: () => {
      invalidate();
      onClose();
    },
  });

  return (
    <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: "100%", sm: 560 } } }}>
      <Box sx={{ p: 2, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Typography variant="h6">{strings.records.editTitle}</Typography>
        <IconButton onClick={onClose} aria-label={strings.common.cancel}>
          <CloseIcon />
        </IconButton>
      </Box>
      <Divider />
      {isLoading && (
        <Box sx={{ p: 2 }}>
          <Typography>{strings.common.loading}</Typography>
        </Box>
      )}
      {record && (
        <Box sx={{ p: 2 }}>
          <Stack spacing={2}>
            {vehicleLabel && (
              <Typography variant="body2" color="text.secondary">
                {strings.reminders.vehicle}: {vehicleLabel}
              </Typography>
            )}

            <FormControl fullWidth size="small" required>
              <InputLabel>{strings.records.serviceType}</InputLabel>
              <Select
                label={strings.records.serviceType}
                value={serviceTypeId}
                onChange={(e) => setServiceTypeId(e.target.value)}
              >
                {(serviceTypes ?? []).map((type) => (
                  <MenuItem key={type.id} value={String(type.id)}>
                    {type.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
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
              onChange={(e) => setOdometerKm(e.target.value)}
              fullWidth
              size="small"
              inputProps={{ min: 0, step: 0.1 }}
            />
            <TextField
              label={strings.records.cost}
              type="number"
              value={cost}
              onChange={(e) => setCost(e.target.value)}
              fullWidth
              size="small"
              inputProps={{ min: 0 }}
              InputProps={{ endAdornment: ` ${strings.logService.currency}` }}
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

            <Divider />
            <PartsPicker
              rows={partRows}
              setRows={setPartRows}
              parts={parts ?? []}
              stockBonus={stockBonus}
              currency={record.currency}
            />

            <Box
              sx={{
                display: "flex",
                gap: 1,
                justifyContent: "space-between",
                flexDirection: { xs: "column", md: "row" },
              }}
            >
              <Button
                variant="outlined"
                color="error"
                startIcon={<DeleteIcon />}
                disabled={deleteMutation.isPending}
                onClick={async () => {
                  if (await confirm(strings.records.deleteConfirm)) {
                    deleteMutation.mutate();
                  }
                }}
              >
                {strings.common.delete}
              </Button>
              <Button
                variant="contained"
                onClick={() => updateMutation.mutate()}
                disabled={
                  updateMutation.isPending || !serviceTypeId || !performedAt
                }
              >
                {strings.records.saveChanges}
              </Button>
            </Box>

            <Divider />
            <Typography variant="subtitle2">{strings.records.editHistory}</Typography>
            {record.changes.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                {strings.records.editHistoryEmpty}
              </Typography>
            ) : (
              <Stack spacing={1}>
                {record.changes.map((change) => {
                  const ago = formatAgo(change.created_at, strings);
                  return (
                    <Box key={change.id}>
                      <Typography variant="body2">
                        {describeChange(strings, change, record.currency)}
                      </Typography>
                      {ago && (
                        <Typography variant="caption" color="text.secondary">
                          {ago}
                        </Typography>
                      )}
                    </Box>
                  );
                })}
              </Stack>
            )}
          </Stack>
        </Box>
      )}
    </Drawer>
  );
}
