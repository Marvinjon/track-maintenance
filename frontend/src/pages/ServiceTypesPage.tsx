import AddIcon from "@mui/icons-material/Add";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Fab,
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
import { useState } from "react";
import { api } from "../api/client";
import type { MaintenanceRecordWithVehicle, ServiceType } from "../api/types";
import { RecordDrawer } from "../components/RecordDrawer";
import { ServiceTypeDrawer } from "../components/ServiceTypeDrawer";
import { TableExportButton } from "../components/TableExportButton";
import { TableImportButton } from "../components/TableImportButton";
import { TablePanel } from "../components/TablePanel";
import { serviceTypesExportSheet } from "../export/datasets";
import {
  SERVICE_TYPES_IMPORT_EXAMPLE,
  SERVICE_TYPES_IMPORT_HEADERS,
} from "../export/importTemplates";
import { useSettingsStyles } from "../styles/useSettingsStyles";
import { useStrings } from "../hooks/useLocale";

function NewServiceTypeDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const strings = useStrings();
  const queryClient = useQueryClient();
  const { classes } = useSettingsStyles();
  const [name, setName] = useState("");
  const [intervalKm, setIntervalKm] = useState("");
  const [intervalDays, setIntervalDays] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      api.createServiceType({
        name: name.trim(),
        default_interval_km: intervalKm === "" ? undefined : Number(intervalKm),
        default_interval_days: intervalDays === "" ? undefined : Number(intervalDays),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["service-types"] });
      setName("");
      setIntervalKm("");
      setIntervalDays("");
      onClose();
    },
  });

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{strings.serviceTypes.newTypeTitle}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <TextField
            label={strings.serviceTypes.name}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            fullWidth
            size="small"
            autoFocus
          />
          <TextField
            label={strings.serviceTypes.defaultIntervalKm}
            type="number"
            value={intervalKm}
            onChange={(e) => setIntervalKm(e.target.value)}
            fullWidth
            size="small"
            inputProps={{ min: 1 }}
          />
          <TextField
            label={strings.serviceTypes.defaultIntervalDays}
            type="number"
            value={intervalDays}
            onChange={(e) => setIntervalDays(e.target.value)}
            fullWidth
            size="small"
            inputProps={{ min: 1 }}
          />
        </Stack>
      </DialogContent>
      <DialogActions className={classes.buttons}>
        <Button variant="outlined" onClick={onClose}>
          {strings.common.cancel}
        </Button>
        <Button
          variant="contained"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || !name.trim()}
        >
          {strings.serviceTypes.create}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default function ServiceTypesPage() {
  const strings = useStrings();
  const { classes } = useSettingsStyles();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedRecord, setSelectedRecord] = useState<MaintenanceRecordWithVehicle | null>(
    null,
  );

  const { data: serviceTypes, isLoading, isError } = useQuery({
    queryKey: ["service-types"],
    queryFn: api.getServiceTypes,
  });

  const selected: ServiceType | null =
    serviceTypes?.find((type) => type.id === selectedId) ?? null;

  if (isLoading) return <Typography>{strings.common.loading}</Typography>;
  if (isError || !serviceTypes) return <Alert severity="error">{strings.common.error}</Alert>;

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2, flexWrap: "wrap", gap: 1 }}>
        <Typography variant="h5">{strings.serviceTypes.title}</Typography>
        <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
          <TableImportButton
            title={strings.import.serviceTypesTitle}
            templateFilename="service-types-import-template"
            templateHeaders={SERVICE_TYPES_IMPORT_HEADERS}
            templateExampleRow={SERVICE_TYPES_IMPORT_EXAMPLE}
            onImport={api.importServiceTypes}
            invalidateQueries={[["service-types"]]}
          />
          <TableExportButton
            filename="service-types"
            sheets={() => [serviceTypesExportSheet(strings, serviceTypes)]}
            disabled={serviceTypes.length === 0}
          />
        </Box>
      </Box>

      {serviceTypes.length === 0 ? (
        <Typography color="text.secondary">{strings.serviceTypes.empty}</Typography>
      ) : (
        <TablePanel>
          <Table className={classes.table} size="small">
            <TableHead>
              <TableRow>
                <TableCell>{strings.serviceTypes.name}</TableCell>
                <TableCell>{strings.serviceTypes.defaultIntervalKm}</TableCell>
                <TableCell className={classes.hideOnMobile}>
                  {strings.serviceTypes.defaultIntervalDays}
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {serviceTypes.map((type) => (
                <TableRow
                  key={type.id}
                  hover
                  sx={{ cursor: "pointer" }}
                  onClick={() => setSelectedId(type.id)}
                >
                  <TableCell>{type.name}</TableCell>
                  <TableCell>
                    {type.default_interval_km?.toLocaleString("en-GB") ??
                      strings.common.notAvailable}
                  </TableCell>
                  <TableCell className={classes.hideOnMobile}>
                    {type.default_interval_days ?? strings.common.notAvailable}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TablePanel>
      )}

      <Fab
        color="primary"
        aria-label={strings.serviceTypes.addType}
        className={classes.fab}
        onClick={() => setDialogOpen(true)}
      >
        <AddIcon />
      </Fab>

      <NewServiceTypeDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
      <ServiceTypeDrawer
        serviceType={selected}
        onClose={() => setSelectedId(null)}
        onRecordClick={(record) => setSelectedRecord(record)}
      />
      <RecordDrawer
        recordId={selectedRecord?.id ?? null}
        vehicleLabel={
          selectedRecord
            ? selectedRecord.vehicle_plate?.trim() ||
              selectedRecord.vehicle_device_name?.trim() ||
              undefined
            : undefined
        }
        onClose={() => setSelectedRecord(null)}
      />
    </>
  );
}
