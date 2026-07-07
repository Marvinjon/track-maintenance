import FileDownloadIcon from "@mui/icons-material/FileDownload";
import { Button, ListItemText, Menu, MenuItem } from "@mui/material";
import { useState } from "react";
import { downloadTableExport, type ExportFormat } from "../export/tableExport";
import { useStrings } from "../hooks/useLocale";

interface Props {
  fromDate: string;
  toDate: string;
  vehicleId?: number;
  onExportSummary: (format: ExportFormat) => void | Promise<void>;
  disabled?: boolean;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function filenameFromContentDisposition(header: string | null): string | null {
  if (!header) return null;
  const match = /filename="?([^";\n]+)"?/i.exec(header);
  return match?.[1] ?? null;
}

export function ReportsExportButton({
  fromDate,
  toDate,
  vehicleId,
  onExportSummary,
  disabled = false,
}: Props) {
  const strings = useStrings();
  const [anchor, setAnchor] = useState<null | HTMLElement>(null);
  const [loading, setLoading] = useState(false);

  const run = async (action: () => void | Promise<void>) => {
    setAnchor(null);
    setLoading(true);
    try {
      await action();
    } finally {
      setLoading(false);
    }
  };

  const recordsCsvUrl = () => {
    const params = new URLSearchParams({ from: fromDate, to: toDate });
    if (vehicleId !== undefined) params.set("vehicle_id", String(vehicleId));
    return `/api/v1/reports/records/export?${params}`;
  };

  const downloadRecordsCsv = async () => {
    const response = await fetch(recordsCsvUrl(), { credentials: "include" });
    if (!response.ok) {
      throw new Error(`Export failed (${response.status})`);
    }
    const blob = await response.blob();
    const filename =
      filenameFromContentDisposition(response.headers.get("Content-Disposition")) ??
      `maintenance-records-${fromDate}-${toDate}.csv`;
    downloadBlob(blob, filename);
  };

  return (
    <>
      <Button
        variant="outlined"
        startIcon={<FileDownloadIcon />}
        disabled={disabled || loading}
        onClick={(event) => setAnchor(event.currentTarget)}
      >
        {loading ? strings.export.exporting : strings.export.button}
      </Button>
      <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
        <MenuItem onClick={() => void run(() => onExportSummary("csv"))}>
          <ListItemText primary={strings.export.csv} secondary={strings.reports.title} />
        </MenuItem>
        <MenuItem onClick={() => void run(() => onExportSummary("xlsx"))}>
          <ListItemText primary={strings.export.xlsx} secondary={strings.reports.title} />
        </MenuItem>
        <MenuItem onClick={() => void run(downloadRecordsCsv)}>
          <ListItemText primary={strings.export.allRecordsCsv} />
        </MenuItem>
      </Menu>
    </>
  );
}

export { downloadTableExport };
