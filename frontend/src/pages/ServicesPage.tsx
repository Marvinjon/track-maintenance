import {
  Alert,
  Box,
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import type { MaintenanceRecordWithVehicle } from "../api/types";
import { NewServiceModal } from "../components/NewServiceModal";
import { RecordDrawer } from "../components/RecordDrawer";
import { TableExportButton } from "../components/TableExportButton";
import { TableImportButton } from "../components/TableImportButton";
import { TablePanel } from "../components/TablePanel";
import { fetchAllRecords, recordsExportSheet } from "../export/datasets";
import {
  RECORDS_IMPORT_EXAMPLE,
  RECORDS_IMPORT_HEADERS,
} from "../export/importTemplates";
import { formatCost, formatKm } from "../format";
import { useSettingsStyles } from "../styles/useSettingsStyles";
import type { Strings } from "../i18n";
import { useStrings } from "../hooks/useLocale";

function vehicleDisplay(strings: Strings, record: MaintenanceRecordWithVehicle): string {
  return (
    record.vehicle_plate?.trim() ||
    record.vehicle_device_name?.trim() ||
    strings.common.notAvailable
  );
}

export default function ServicesPage() {
  const strings = useStrings();
  const { classes } = useSettingsStyles();
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<MaintenanceRecordWithVehicle | null>(
    null,
  );
  const [limit, setLimit] = useState(20);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["all-records", limit],
    queryFn: () => api.getAllRecords(limit, 0),
  });

  if (isLoading) return <Typography>{strings.common.loading}</Typography>;
  if (isError || !data) return <Alert severity="error">{strings.common.error}</Alert>;

  const loadedTotal = data.items.reduce((sum, record) => {
    if (record.cost === null) return sum;
    return sum + Number(record.cost);
  }, 0);
  const currency = data.items[0]?.currency ?? "ISK";

  return (
    <>
      <Box className={classes.pageHeader}>
        <Typography variant="h5">{strings.services.title}</Typography>
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", alignItems: "center" }}>
          <TableImportButton
            title={strings.import.servicesTitle}
            templateFilename="services-import-template"
            templateHeaders={RECORDS_IMPORT_HEADERS}
            templateExampleRow={RECORDS_IMPORT_EXAMPLE}
            onImport={api.importRecords}
            invalidateQueries={[["all-records"], ["dashboard"]]}
          />
          <TableExportButton
            filename="services"
            sheets={async () => [recordsExportSheet(strings, await fetchAllRecords())]}
            disabled={data.total === 0}
          />
          <Button variant="contained" onClick={() => setModalOpen(true)}>
            {strings.services.newService}
          </Button>
        </Box>
      </Box>

      {data.items.length === 0 ? (
        <Typography color="text.secondary">{strings.services.empty}</Typography>
      ) : (
        <TablePanel>
          <Table className={classes.table} size="small">
            <TableHead>
              <TableRow>
                <TableCell>{strings.reminders.vehicle}</TableCell>
                <TableCell>{strings.records.date}</TableCell>
                <TableCell>{strings.records.serviceType}</TableCell>
                <TableCell className={classes.hideOnMobile}>{strings.records.odometerKm}</TableCell>
                <TableCell>{strings.records.cost}</TableCell>
                <TableCell className={classes.hideOnMobile}>{strings.records.performedBy}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.items.map((record) => (
                <TableRow
                  key={record.id}
                  hover
                  sx={{ cursor: "pointer" }}
                  onClick={() => setSelectedRecord(record)}
                >
                  <TableCell>{vehicleDisplay(strings, record)}</TableCell>
                  <TableCell>{record.performed_at}</TableCell>
                  <TableCell>{record.service_type_name}</TableCell>
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

      {data.total > data.items.length && (
        <Button variant="text" onClick={() => setLimit((value) => value + 20)} sx={{ mt: 1 }}>
          {strings.records.loadMore}
        </Button>
      )}

      {data.items.length > 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {strings.services.loadedTotal(formatCost(String(loadedTotal), currency))}
        </Typography>
      )}

      <NewServiceModal open={modalOpen} onClose={() => setModalOpen(false)} />
      <RecordDrawer
        recordId={selectedRecord?.id ?? null}
        vehicleLabel={selectedRecord ? vehicleDisplay(strings, selectedRecord) : undefined}
        onClose={() => setSelectedRecord(null)}
      />
    </>
  );
}
