import FileDownloadIcon from "@mui/icons-material/FileDownload";
import { Button, ListItemText, Menu, MenuItem } from "@mui/material";
import { useState } from "react";
import { api } from "../api/client";
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

  const downloadRecordsCsv = async () => {
    const { blob, filename } = await api.downloadRecordsExport(fromDate, toDate, vehicleId);
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
