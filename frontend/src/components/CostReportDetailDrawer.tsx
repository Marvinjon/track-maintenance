import CloseIcon from "@mui/icons-material/Close";
import {
  Box,
  Divider,
  Drawer,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { MonthlyCostRow } from "../api/types";
import { costReportDetailSheets } from "../export/datasets";
import { RecordDrawer } from "./RecordDrawer";
import { TableExportButton } from "./TableExportButton";
import { TablePanel } from "./TablePanel";
import { formatCost, formatKm } from "../format";
import { useSettingsStyles } from "../styles/useSettingsStyles";
import { useLocale, useStrings } from "../hooks/useLocale";
import { useState } from "react";

function monthLabel(year: number, month: number): string {
  return new Date(year, month - 1, 1).toLocaleDateString("en-GB", {
    month: "long",
    year: "numeric",
  });
}

type Selection = Pick<MonthlyCostRow, "vehicle_id" | "year" | "month">;

interface Props {
  selection: Selection | null;
  onClose: () => void;
}

export function CostReportDetailDrawer({ selection, onClose }: Props) {
  const strings = useStrings();
  const { locale } = useLocale();
  const { classes } = useSettingsStyles();
  const [selectedRecordId, setSelectedRecordId] = useState<number | null>(null);
  const open = selection !== null;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["cost-report-detail", selection?.vehicle_id, selection?.year, selection?.month],
    queryFn: () =>
      api.getCostReportDetail(selection!.vehicle_id, selection!.year, selection!.month),
    enabled: open,
  });

  const vehicleLabel =
    data?.vehicle_plate?.trim() ||
    data?.vehicle_device_name?.trim() ||
    strings.common.notAvailable;

  return (
    <>
      <Drawer
        anchor="right"
        open={open}
        onClose={onClose}
        PaperProps={{ sx: { width: { xs: "100%", sm: 560, md: 640 } } }}
      >
        <Box sx={{ p: 2, display: "flex", alignItems: "flex-start", gap: 1 }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="h6" noWrap>
              {data ? monthLabel(data.year, data.month) : strings.reports.detailTitle}
            </Typography>
            {data && (
              <Typography variant="body2" color="text.secondary">
                {vehicleLabel}
              </Typography>
            )}
          </Box>
          {data && (
            <TableExportButton
              filename={`cost-detail-${data.year}-${String(data.month).padStart(2, "0")}-${data.vehicle_id}`}
              sheets={() => costReportDetailSheets(strings, locale, data)}
              disabled={data.records.length === 0}
            />
          )}
          <IconButton onClick={onClose} aria-label={strings.common.cancel}>
            <CloseIcon />
          </IconButton>
        </Box>
        <Divider />

        <Box sx={{ p: 2, overflowY: "auto" }}>
          {isLoading && <Typography>{strings.common.loading}</Typography>}
          {isError && (
            <Typography color="error">{strings.common.error}</Typography>
          )}
          {data && (
            <Stack spacing={3}>
              <Stack direction="row" spacing={3} flexWrap="wrap">
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    {strings.reports.totalCost}
                  </Typography>
                  <Typography variant="h6">
                    {formatCost(data.total_cost, data.currency)}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    {strings.reports.laborCost}
                  </Typography>
                  <Typography variant="body1">
                    {formatCost(data.labor_cost, data.currency)}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    {strings.reports.partsCost}
                  </Typography>
                  <Typography variant="body1">
                    {formatCost(data.parts_cost, data.currency)}
                  </Typography>
                </Box>
              </Stack>

              {data.service_type_breakdown.length > 0 && (
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    {strings.reports.byServiceType}
                  </Typography>
                  <TablePanel>
                    <Table size="small" className={classes.table}>
                      <TableHead>
                        <TableRow>
                          <TableCell>{strings.records.serviceType}</TableCell>
                          <TableCell>{strings.reports.laborCost}</TableCell>
                          <TableCell>{strings.reports.partsCost}</TableCell>
                          <TableCell>{strings.reports.totalCost}</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {data.service_type_breakdown.map((row) => (
                          <TableRow key={row.service_type_id}>
                            <TableCell>
                              {row.service_type_name}
                              <Typography variant="caption" color="text.secondary" display="block">
                                {strings.reports.recordCountLabel(row.record_count)}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              {formatCost(row.labor_cost, data.currency)}
                            </TableCell>
                            <TableCell>
                              {formatCost(row.parts_cost, data.currency)}
                            </TableCell>
                            <TableCell>
                              {formatCost(row.total_cost, data.currency)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TablePanel>
                </Box>
              )}

              {data.parts_summary.length > 0 && (
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    {strings.reports.partsInventory}
                  </Typography>
                  <TablePanel>
                    <Table size="small" className={classes.table}>
                      <TableHead>
                        <TableRow>
                          <TableCell>{strings.parts.name}</TableCell>
                          <TableCell className={classes.hideOnMobile}>{strings.parts.sku}</TableCell>
                          <TableCell>{strings.ledger.quantity}</TableCell>
                          <TableCell>{strings.reports.totalCost}</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {data.parts_summary.map((part) => (
                          <TableRow key={part.part_id}>
                            <TableCell>{part.part_name}</TableCell>
                            <TableCell className={classes.hideOnMobile}>
                              {part.sku ?? strings.common.notAvailable}
                            </TableCell>
                            <TableCell>
                              {Number(part.total_quantity).toLocaleString("en-GB")} {part.unit}
                            </TableCell>
                            <TableCell>
                              {formatCost(part.total_cost, data.currency)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TablePanel>
                </Box>
              )}

              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  {strings.reports.services}
                </Typography>
                {data.records.length === 0 ? (
                  <Typography color="text.secondary">{strings.reports.empty}</Typography>
                ) : (
                  <Stack spacing={2}>
                    {data.records.map((record) => (
                      <Box
                        key={record.id}
                        sx={{
                          border: 1,
                          borderColor: "divider",
                          borderRadius: 1,
                          overflow: "hidden",
                          cursor: "pointer",
                          "&:hover": { bgcolor: "action.hover" },
                        }}
                        onClick={() => setSelectedRecordId(record.id)}
                      >
                        <Box sx={{ p: 1.5, bgcolor: "action.selected" }}>
                          <Stack
                            direction="row"
                            justifyContent="space-between"
                            alignItems="flex-start"
                            gap={1}
                          >
                            <Box>
                              <Typography variant="body2" fontWeight={600}>
                                {record.service_type_name}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {record.performed_at}
                                {record.odometer_km !== null &&
                                  ` · ${formatKm(record.odometer_km)}`}
                                {record.performed_by && ` · ${record.performed_by}`}
                              </Typography>
                            </Box>
                            <Typography variant="body2" fontWeight={600}>
                              {formatCost(record.total_cost, record.currency)}
                            </Typography>
                          </Stack>
                        </Box>
                        {(record.labor_cost !== null || record.parts.length > 0) && (
                          <Box sx={{ px: 1.5, py: 1 }}>
                            {record.labor_cost !== null && (
                              <Typography variant="caption" color="text.secondary" display="block">
                                {strings.reports.laborCost}:{" "}
                                {formatCost(record.labor_cost, record.currency)}
                              </Typography>
                            )}
                            {record.parts.length > 0 && (
                              <Table size="small" sx={{ mt: 0.5 }}>
                                <TableHead>
                                  <TableRow>
                                    <TableCell sx={{ py: 0.5, pl: 0 }}>
                                      {strings.parts.name}
                                    </TableCell>
                                    <TableCell sx={{ py: 0.5 }} align="right">
                                      {strings.ledger.quantity}
                                    </TableCell>
                                    <TableCell sx={{ py: 0.5 }} align="right">
                                      {strings.reports.lineCost}
                                    </TableCell>
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  {record.parts.map((part) => (
                                    <TableRow key={`${record.id}-${part.part_id}`}>
                                      <TableCell sx={{ py: 0.5, pl: 0, border: 0 }}>
                                        <Typography variant="caption">
                                          {part.part_name}
                                          {part.sku && ` (${part.sku})`}
                                        </Typography>
                                      </TableCell>
                                      <TableCell sx={{ py: 0.5, border: 0 }} align="right">
                                        <Typography variant="caption">
                                          {Number(part.quantity).toLocaleString("en-GB")}{" "}
                                          {part.unit}
                                        </Typography>
                                      </TableCell>
                                      <TableCell sx={{ py: 0.5, border: 0 }} align="right">
                                        <Typography variant="caption">
                                          {formatCost(part.line_cost, record.currency)}
                                        </Typography>
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            )}
                          </Box>
                        )}
                      </Box>
                    ))}
                  </Stack>
                )}
              </Box>
            </Stack>
          )}
        </Box>
      </Drawer>

      <RecordDrawer
        recordId={selectedRecordId}
        vehicleLabel={vehicleLabel}
        onClose={() => setSelectedRecordId(null)}
      />
    </>
  );
}
