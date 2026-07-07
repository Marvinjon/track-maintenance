import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import {
  Alert,
  Box,
  Button,
  IconButton,
  Stack,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { VehicleDetail } from "../api/types";
import { LogServiceModal } from "../components/LogServiceModal";
import { TransferTrackerModal } from "../components/TransferTrackerModal";
import { ReminderBadge } from "../components/ReminderBadge";
import { RemindersTab } from "../components/RemindersTab";
import { TableExportButton } from "../components/TableExportButton";
import { TablePanel } from "../components/TablePanel";
import {
  fetchVehicleRecords,
  vehicleRecordsExportSheet,
} from "../export/datasets";
import { formatAgo, formatCost, formatKm } from "../format";
import { traccarDeviceUrl, useTraccarPublicUrl } from "../hooks/useTraccarUrl";
import { useSettingsStyles } from "../styles/useSettingsStyles";
import { useStrings } from "../hooks/useLocale";
import { useConfirm } from "../hooks/useConfirm";

function RecordsTab({ vehicle }: { vehicle: VehicleDetail }) {
  const strings = useStrings();
  const confirm = useConfirm();
  const queryClient = useQueryClient();
  const { classes } = useSettingsStyles();
  const [modalOpen, setModalOpen] = useState(false);
  const [limit, setLimit] = useState(20);

  const { data, isLoading } = useQuery({
    queryKey: ["records", vehicle.id, limit],
    queryFn: () => api.getRecords(vehicle.id!, limit, 0),
  });

  const deleteMutation = useMutation({
    mutationFn: (recordId: number) => api.deleteRecord(recordId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["records", vehicle.id] });
      queryClient.invalidateQueries({ queryKey: ["vehicle", vehicle.id] });
      queryClient.invalidateQueries({ queryKey: ["vehicles"] });
    },
  });

  const vehicleLabel =
    vehicle.plate?.trim() || vehicle.device_name?.trim() || strings.common.notAvailable;

  return (
    <Stack spacing={2} sx={{ mt: 2 }}>
      <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 1, flexWrap: "wrap" }}>
        {data && data.total > 0 && (
          <TableExportButton
            filename={`vehicle-${vehicle.id}-records`}
            sheets={async () => [
              vehicleRecordsExportSheet(strings, await fetchVehicleRecords(vehicle.id!), vehicleLabel),
            ]}
          />
        )}
        <Button
          variant="contained"
          onClick={() => setModalOpen(true)}
          disabled={vehicle.archived}
        >
          {strings.vehicleDetail.logService}
        </Button>
      </Box>

      {isLoading && <Typography>{strings.common.loading}</Typography>}
      {data && data.items.length === 0 && (
        <Typography color="text.secondary">{strings.vehicleDetail.noRecords}</Typography>
      )}
      {data && data.items.length > 0 && (
        <TablePanel>
          <Table size="small" className={classes.table}>
            <TableHead>
              <TableRow>
                <TableCell>{strings.records.date}</TableCell>
                <TableCell>{strings.records.serviceType}</TableCell>
                <TableCell>{strings.records.odometerKm}</TableCell>
                <TableCell>{strings.records.cost}</TableCell>
                <TableCell className={classes.hideOnMobile}>{strings.records.performedBy}</TableCell>
                <TableCell className={classes.hideOnMobile}>{strings.records.notes}</TableCell>
                <TableCell className={classes.columnAction} />
              </TableRow>
            </TableHead>
            <TableBody>
              {data.items.map((record) => (
                <TableRow key={record.id}>
                  <TableCell>{record.performed_at}</TableCell>
                  <TableCell>{record.service_type_name}</TableCell>
                  <TableCell>{formatKm(record.odometer_km)}</TableCell>
                  <TableCell>{formatCost(record.cost, record.currency)}</TableCell>
                  <TableCell className={classes.hideOnMobile}>
                    {record.performed_by ?? strings.common.notAvailable}
                  </TableCell>
                  <TableCell className={classes.hideOnMobile}>
                    <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
                      {record.notes}
                    </Typography>
                  </TableCell>
                  <TableCell className={classes.columnAction}>
                    <IconButton
                      size="small"
                      color="error"
                      aria-label={strings.common.delete}
                      disabled={deleteMutation.isPending}
                      onClick={async () => {
                        if (await confirm(strings.records.deleteConfirm)) {
                          deleteMutation.mutate(record.id);
                        }
                      }}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TablePanel>
      )}
      {data && data.total > data.items.length && (
        <Button variant="text" onClick={() => setLimit((l) => l + 20)}>
          {strings.records.loadMore}
        </Button>
      )}

      <LogServiceModal
        vehicle={{
          id: vehicle.id!,
          odometer_km_cached: vehicle.odometer_km_cached,
        }}
        open={modalOpen}
        onClose={() => setModalOpen(false)}
      />
    </Stack>
  );
}

function VehiclePlateSection({ vehicle }: { vehicle: VehicleDetail }) {
  const strings = useStrings();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [plate, setPlate] = useState(vehicle.plate ?? "");

  useEffect(() => {
    setPlate(vehicle.plate ?? "");
    setEditing(false);
  }, [vehicle.id, vehicle.plate]);

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updateVehicle(vehicle.id!, {
        plate: plate.trim() === "" ? null : plate.trim(),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vehicle", vehicle.id] });
      queryClient.invalidateQueries({ queryKey: ["vehicles"] });
      setEditing(false);
    },
  });

  const title =
    vehicle.plate ??
    vehicle.device_name ??
    [vehicle.make, vehicle.model].filter(Boolean).join(" ");

  const startEdit = () => {
    setPlate(vehicle.plate ?? "");
    setEditing(true);
  };

  const cancelEdit = () => {
    setPlate(vehicle.plate ?? "");
    setEditing(false);
  };

  const canSave = plate.trim() !== (vehicle.plate ?? "");

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
        <Typography variant="h5">{title}</Typography>
        {vehicle.plate && !editing && (
          <IconButton
            size="small"
            onClick={startEdit}
            aria-label={strings.vehicleDetail.editPlate}
          >
            <EditIcon fontSize="small" />
          </IconButton>
        )}
      </Box>
      {vehicle.device_name && title !== vehicle.device_name && (
        <Typography variant="body2" color="text.secondary">
          {strings.vehicleDetail.deviceLabel(vehicle.device_name)}
        </Typography>
      )}
      {!vehicle.plate && !editing && (
        <Button
          size="small"
          variant="outlined"
          onClick={startEdit}
          sx={{ mt: 1 }}
        >
          {strings.vehicleDetail.addPlate}
        </Button>
      )}
      {editing && (
        <Box
          sx={{
            mt: 1,
            display: "flex",
            gap: 1,
            alignItems: "flex-start",
            flexWrap: "wrap",
          }}
        >
          <TextField
            label={strings.vehicles.plate}
            value={plate}
            onChange={(event) => setPlate(event.target.value)}
            size="small"
            sx={{ minWidth: 180 }}
            slotProps={{ htmlInput: { maxLength: 20 } }}
            autoFocus
          />
          <Button
            variant="contained"
            onClick={() => saveMutation.mutate()}
            disabled={!canSave || saveMutation.isPending}
          >
            {strings.common.save}
          </Button>
          <Button variant="text" onClick={cancelEdit} disabled={saveMutation.isPending}>
            {strings.common.cancel}
          </Button>
        </Box>
      )}
      {saveMutation.isError && (
        <Typography variant="body2" color="error" sx={{ mt: 1 }}>
          {strings.vehicleDetail.saveFailed}
        </Typography>
      )}
    </Box>
  );
}

export default function VehicleDetailPage() {
  const strings = useStrings();
  const { vehicleId } = useParams();
  const navigate = useNavigate();
  const id = Number(vehicleId);
  const queryClient = useQueryClient();
  const theme = useTheme();
  const desktop = useMediaQuery(theme.breakpoints.up("md"));
  const traccarPublicUrl = useTraccarPublicUrl();
  const [tab, setTab] = useState(0);
  const [transferOpen, setTransferOpen] = useState(false);

  const { data: vehicle, isLoading, isError } = useQuery({
    queryKey: ["vehicle", id],
    queryFn: () => api.getVehicle(id),
    enabled: Number.isFinite(id),
  });

  const syncMutation = useMutation({
    mutationFn: () => api.syncOdometer(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vehicle", id] });
      queryClient.invalidateQueries({ queryKey: ["vehicles"] });
    },
  });

  const maintenanceSyncMutation = useMutation({
    mutationFn: () => api.syncMaintenance(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vehicle", id] });
      queryClient.invalidateQueries({ queryKey: ["vehicles"] });
      queryClient.invalidateQueries({ queryKey: ["reminders", id] });
    },
  });

  if (isLoading) return <Typography>{strings.common.loading}</Typography>;
  if (isError || !vehicle) return <Alert severity="error">{strings.common.error}</Alert>;

  const ago = formatAgo(vehicle.odometer_synced_at, strings);

  return (
    <Stack spacing={2}>
      {vehicle.archived && (
        <Alert severity="info">{strings.vehicleDetail.archivedBanner}</Alert>
      )}
      <Button
        component={Link}
        to="/vehicles"
        startIcon={<ArrowBackIcon />}
        size="small"
        sx={{ alignSelf: "flex-start" }}
      >
        {strings.vehicleDetail.back}
      </Button>

      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
          flexWrap: "wrap",
          gap: 2,
          flexDirection: { xs: "column", md: "row" },
        }}
      >
        <Box sx={{ width: { xs: "100%", md: "auto" } }}>
          <VehiclePlateSection vehicle={vehicle} />
          <Box sx={{ display: "flex", gap: 1, alignItems: "center", mt: 1.5, flexWrap: "wrap" }}>
            <Tooltip
              title={ago ? strings.vehicles.syncedAgo(ago) : strings.vehicles.neverSynced}
            >
              <Typography variant="h6">{formatKm(vehicle.odometer_km_cached)}</Typography>
            </Tooltip>
            {vehicle.engine_hours_cached !== null && (
              <Typography variant="body2" color="text.secondary">
                {Number(vehicle.engine_hours_cached).toLocaleString("en-GB")} h
              </Typography>
            )}
            <ReminderBadge status={vehicle.reminder_status} />
          </Box>
        </Box>
        <Box sx={{ display: "flex", gap: 1, alignItems: "center", width: { xs: "100%", md: "auto" } }}>
          {syncMutation.isError && (
            <Typography variant="body2" color="error">
              {strings.vehicleDetail.syncFailed}
            </Typography>
          )}
          {traccarPublicUrl && (
            <Button
              variant="text"
              endIcon={<OpenInNewIcon fontSize="small" />}
              href={traccarDeviceUrl(traccarPublicUrl, vehicle.traccar_device_id)}
              target="_blank"
              rel="noopener noreferrer"
            >
              {strings.vehicleDetail.viewInTraccar}
            </Button>
          )}
          {!vehicle.archived && (
            <Button variant="outlined" onClick={() => setTransferOpen(true)}>
              {strings.vehicleDetail.transferTracker}
            </Button>
          )}
          {!vehicle.archived && (
            <Button
              variant="outlined"
              onClick={() => maintenanceSyncMutation.mutate()}
              disabled={maintenanceSyncMutation.isPending}
            >
              {maintenanceSyncMutation.isPending
                ? strings.vehicleDetail.syncingMaintenance
                : strings.vehicleDetail.syncMaintenance}
            </Button>
          )}
          <Button
            variant="outlined"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending || vehicle.archived}
          >
            {strings.vehicleDetail.syncNow}
          </Button>
        </Box>
      </Box>

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        variant={desktop ? "standard" : "scrollable"}
        scrollButtons={desktop ? false : "auto"}
      >
        <Tab label={strings.vehicleDetail.tabs.records} />
        <Tab label={strings.vehicleDetail.tabs.reminders} />
      </Tabs>
      {tab === 0 && <RecordsTab vehicle={vehicle} />}
      {tab === 1 && <RemindersTab vehicle={vehicle} />}
      {!vehicle.archived && (
        <TransferTrackerModal
          vehicle={vehicle}
          open={transferOpen}
          onClose={() => setTransferOpen(false)}
          onTransferred={(newVehicleId) => {
            queryClient.invalidateQueries({ queryKey: ["vehicles"] });
            setTransferOpen(false);
            navigate(`/vehicles/${newVehicleId}`);
          }}
        />
      )}
    </Stack>
  );
}
