import FileDownloadIcon from "@mui/icons-material/FileDownload";
import { Button, ListItemText, Menu, MenuItem } from "@mui/material";
import { useState } from "react";
import { downloadTableExport, type ExportFormat, type ExportSheet } from "../export/tableExport";
import { useStrings } from "../hooks/useLocale";

interface Props {
  filename: string;
  sheets: ExportSheet[] | (() => ExportSheet[] | Promise<ExportSheet[]>);
  disabled?: boolean;
  size?: "small" | "medium";
  variant?: "outlined" | "text" | "contained";
}

export function TableExportButton({
  filename,
  sheets,
  disabled = false,
  size = "small",
  variant = "outlined",
}: Props) {
  const strings = useStrings();
  const [anchor, setAnchor] = useState<null | HTMLElement>(null);
  const [loading, setLoading] = useState(false);

  const runExport = async (format: ExportFormat) => {
    setAnchor(null);
    setLoading(true);
    try {
      const resolved = typeof sheets === "function" ? await sheets() : sheets;
      if (resolved.length === 0 || resolved.every((s) => s.rows.length === 0)) return;
      downloadTableExport(format, filename, resolved);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Button
        variant={variant}
        size={size}
        startIcon={<FileDownloadIcon />}
        disabled={disabled || loading}
        onClick={(event) => setAnchor(event.currentTarget)}
      >
        {loading ? strings.export.exporting : strings.export.button}
      </Button>
      <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
        <MenuItem onClick={() => void runExport("csv")}>
          <ListItemText primary={strings.export.csv} />
        </MenuItem>
        <MenuItem onClick={() => void runExport("xlsx")}>
          <ListItemText primary={strings.export.xlsx} />
        </MenuItem>
      </Menu>
    </>
  );
}
