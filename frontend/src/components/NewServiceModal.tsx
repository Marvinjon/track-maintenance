import {
  Autocomplete,
  Dialog,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "../api/client";
import type { Vehicle } from "../api/types";
import type { Strings } from "../i18n";
import { useStrings } from "../hooks/useLocale";
import { LogServiceModal } from "./LogServiceModal";

interface Props {
  open: boolean;
  onClose: () => void;
}

function vehicleLabel(strings: Strings, vehicle: Vehicle): string {
  const plate = vehicle.plate?.trim();
  const device = vehicle.device_name?.trim();
  if (plate && device) return `${plate} — ${device}`;
  return plate || device || strings.common.notAvailable;
}

export function NewServiceModal({ open, onClose }: Props) {
  const strings = useStrings();
  const { data: vehicles } = useQuery({
    queryKey: ["vehicles"],
    queryFn: api.getVehicles,
    enabled: open,
  });

  const registered = useMemo(
    () => (vehicles ?? []).filter((v) => v.registered && v.id !== null),
    [vehicles],
  );

  const [selected, setSelected] = useState<Vehicle | null>(null);

  const handleClose = () => {
    setSelected(null);
    onClose();
  };

  if (selected?.id !== null && selected?.id !== undefined) {
    return (
      <LogServiceModal
        key={selected.id}
        vehicle={{
          id: selected.id,
          odometer_km_cached: selected.odometer_km_cached,
        }}
        open={open}
        onClose={handleClose}
      />
    );
  }

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>{strings.logService.title}</DialogTitle>
      <DialogContent>
        <Autocomplete
          sx={{ mt: 1 }}
          options={registered}
          getOptionLabel={(vehicle) => vehicleLabel(strings, vehicle)}
          filterOptions={(options, { inputValue }) => {
            const q = inputValue.trim().toLowerCase();
            if (!q) return options;
            return options.filter((vehicle) => {
              const plate = vehicle.plate?.toLowerCase() ?? "";
              const device = vehicle.device_name?.toLowerCase() ?? "";
              return plate.includes(q) || device.includes(q);
            });
          }}
          value={selected}
          onChange={(_, value) => setSelected(value)}
          renderInput={(params) => (
            <TextField
              {...params}
              label={strings.services.selectVehicle}
              placeholder={strings.services.selectVehicle}
              autoFocus
            />
          )}
          noOptionsText={strings.vehicles.empty}
        />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          {strings.services.noVehicleSelected}
        </Typography>
      </DialogContent>
    </Dialog>
  );
}
