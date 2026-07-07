import {
  Alert,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { VehicleDetail } from "../api/types";
import { useSettingsStyles } from "../styles/useSettingsStyles";
import { useStrings } from "../hooks/useLocale";

interface Props {
  vehicle: VehicleDetail;
  open: boolean;
  onClose: () => void;
  onTransferred: (newVehicleId: number) => void;
}

export function TransferTrackerModal({
  vehicle,
  open,
  onClose,
  onTransferred,
}: Props) {
  const strings = useStrings();
  const { classes } = useSettingsStyles();
  const [plate, setPlate] = useState("");
  const [make, setMake] = useState("");
  const [model, setModel] = useState("");
  const [year, setYear] = useState("");
  const [vin, setVin] = useState("");
  const [notes, setNotes] = useState("");
  const [syncOdometer, setSyncOdometer] = useState(true);
  const [createDefaultReminders, setCreateDefaultReminders] = useState(false);

  useEffect(() => {
    if (open) {
      setPlate("");
      setMake("");
      setModel("");
      setYear("");
      setVin("");
      setNotes("");
      setSyncOdometer(true);
      setCreateDefaultReminders(false);
    }
  }, [open, vehicle.id]);

  const mutation = useMutation({
    mutationFn: () =>
      api.transferTracker(vehicle.id!, {
        plate: plate.trim() === "" ? null : plate.trim(),
        make: make.trim() === "" ? null : make.trim(),
        model: model.trim() === "" ? null : model.trim(),
        year: year === "" ? null : Number(year),
        vin: vin.trim() === "" ? null : vin.trim(),
        notes: notes.trim() === "" ? null : notes.trim(),
        sync_odometer: syncOdometer,
        create_default_reminders: createDefaultReminders,
      }),
    onSuccess: (result) => {
      if (result.vehicle.id !== null) {
        onTransferred(result.vehicle.id);
      }
    },
  });

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{strings.vehicleDetail.transferTitle}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} className={classes.details} sx={{ pt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            {strings.vehicleDetail.transferIntro}
          </Typography>
          {vehicle.device_name && (
            <Typography variant="body2" color="text.secondary">
              {strings.vehicleDetail.deviceLabel(vehicle.device_name)}
            </Typography>
          )}
          <TextField
            label={strings.vehicleDetail.transferPlate}
            value={plate}
            onChange={(e) => setPlate(e.target.value)}
            size="small"
            fullWidth
            autoFocus
            slotProps={{ htmlInput: { maxLength: 20 } }}
          />
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <TextField
              label={strings.vehicleDetail.transferMake}
              value={make}
              onChange={(e) => setMake(e.target.value)}
              size="small"
              fullWidth
            />
            <TextField
              label={strings.vehicleDetail.transferModel}
              value={model}
              onChange={(e) => setModel(e.target.value)}
              size="small"
              fullWidth
            />
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <TextField
              label={strings.vehicleDetail.transferYear}
              type="number"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              size="small"
              fullWidth
            />
            <TextField
              label={strings.vehicleDetail.transferVin}
              value={vin}
              onChange={(e) => setVin(e.target.value)}
              size="small"
              fullWidth
              slotProps={{ htmlInput: { maxLength: 32 } }}
            />
          </Stack>
          <TextField
            label={strings.vehicleDetail.transferNotes}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            size="small"
            fullWidth
            multiline
            minRows={2}
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={syncOdometer}
                onChange={(e) => setSyncOdometer(e.target.checked)}
              />
            }
            label={strings.vehicleDetail.transferSyncOdometer}
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={createDefaultReminders}
                onChange={(e) => setCreateDefaultReminders(e.target.checked)}
              />
            }
            label={strings.vehicleDetail.transferDefaultReminders}
          />
          {mutation.isError && (
            <Alert severity="error">{strings.vehicleDetail.transferFailed}</Alert>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={mutation.isPending}>
          {strings.common.cancel}
        </Button>
        <Button
          variant="contained"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
        >
          {mutation.isPending
            ? strings.vehicleDetail.transferSubmitting
            : strings.vehicleDetail.transferSubmit}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
