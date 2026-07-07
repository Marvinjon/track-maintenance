import FileUploadIcon from "@mui/icons-material/FileUpload";
import { IconButton, Tooltip } from "@mui/material";
import { useState } from "react";
import type { ImportResult } from "../api/types";
import { useStrings } from "../hooks/useLocale";
import { ImportDataDialog } from "./ImportDataDialog";

export interface TableImportButtonProps {
  title: string;
  templateFilename: string;
  templateHeaders: string[];
  templateExampleRow?: string[];
  onImport: (rows: Record<string, string>[]) => Promise<ImportResult>;
  invalidateQueries: string[][];
}

export function TableImportButton({
  title,
  templateFilename,
  templateHeaders,
  templateExampleRow,
  onImport,
  invalidateQueries,
}: TableImportButtonProps) {
  const strings = useStrings();
  const [open, setOpen] = useState(false);

  return (
    <>
      <Tooltip title={strings.import.button}>
        <IconButton size="small" onClick={() => setOpen(true)} aria-label={strings.import.button}>
          <FileUploadIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <ImportDataDialog
        open={open}
        onClose={() => setOpen(false)}
        title={title}
        templateFilename={templateFilename}
        templateHeaders={templateHeaders}
        templateExampleRow={templateExampleRow}
        onImport={onImport}
        invalidateQueries={invalidateQueries}
      />
    </>
  );
}
