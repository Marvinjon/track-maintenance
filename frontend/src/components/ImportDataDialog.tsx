import FileUploadIcon from "@mui/icons-material/FileUpload";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  List,
  ListItem,
  ListItemText,
  Stack,
  Typography,
} from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import type { ImportResult } from "../api/types";
import { downloadTemplate, parseCsvFile } from "../export/csvImport";
import { useStrings } from "../hooks/useLocale";
import { useSettingsStyles } from "../styles/useSettingsStyles";

export interface ImportDataDialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  templateFilename: string;
  templateHeaders: string[];
  templateExampleRow?: string[];
  onImport: (rows: Record<string, string>[]) => Promise<ImportResult>;
  invalidateQueries: string[][];
}

export function ImportDataDialog({
  open,
  onClose,
  title,
  templateFilename,
  templateHeaders,
  templateExampleRow,
  onImport,
  invalidateQueries,
}: ImportDataDialogProps) {
  const strings = useStrings();
  const { classes } = useSettingsStyles();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const [rows, setRows] = useState<Record<string, string>[]>([]);
  const [parseError, setParseError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);

  const resetState = () => {
    setFilename(null);
    setRows([]);
    setParseError(null);
    setResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleClose = () => {
    resetState();
    onClose();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setParseError(null);
    setResult(null);
    setFilename(file.name);

    try {
      const parsed = await parseCsvFile(file);
      setRows(parsed);
    } catch {
      setRows([]);
      setParseError(strings.import.parseError);
    }
  };

  const mutation = useMutation({
    mutationFn: () => onImport(rows),
    onSuccess: async (importResult) => {
      setResult(importResult);
      if (importResult.created > 0) {
        await Promise.all(
          invalidateQueries.map((queryKey) =>
            queryClient.invalidateQueries({ queryKey }),
          ),
        );
      }
    },
  });

  const hasResult = result !== null;
  const canImport = rows.length > 0 && !parseError && !mutation.isPending && !hasResult;

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            {strings.import.instructions}
          </Typography>

          <Button
            variant="outlined"
            size="small"
            onClick={() =>
              downloadTemplate(templateFilename, templateHeaders, templateExampleRow)
            }
          >
            {strings.import.downloadTemplate}
          </Button>

          <Box>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              hidden
              onChange={(event) => void handleFileChange(event)}
            />
            <Button
              variant="outlined"
              size="small"
              startIcon={<FileUploadIcon />}
              onClick={() => fileInputRef.current?.click()}
            >
              {strings.import.chooseFile}
            </Button>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {filename ?? strings.import.noFile}
            </Typography>
            {rows.length > 0 && !parseError && (
              <Typography variant="body2" sx={{ mt: 0.5 }}>
                {strings.import.rowCount(rows.length)}
              </Typography>
            )}
          </Box>

          {parseError && <Alert severity="error">{parseError}</Alert>}

          {mutation.isError && (
            <Alert severity="error">
              {mutation.error instanceof Error
                ? mutation.error.message
                : strings.common.error}
            </Alert>
          )}

          {result && (
            <Box>
              <Stack direction="row" spacing={2} flexWrap="wrap" sx={{ mb: 1 }}>
                {result.created > 0 && (
                  <Typography variant="body2" color="success.main">
                    {strings.import.resultCreated(result.created)}
                  </Typography>
                )}
                {result.skipped > 0 && (
                  <Typography variant="body2" color="text.secondary">
                    {strings.import.resultSkipped(result.skipped)}
                  </Typography>
                )}
                {result.errors.length > 0 && (
                  <Typography variant="body2" color="error.main">
                    {strings.import.resultErrors(result.errors.length)}
                  </Typography>
                )}
              </Stack>
              {result.errors.length > 0 && (
                <List dense disablePadding sx={{ maxHeight: 160, overflow: "auto" }}>
                  {result.errors.map((error) => (
                    <ListItem key={`${error.row}-${error.message}`} disableGutters>
                      <ListItemText
                        primary={strings.import.rowError(error.row, error.message)}
                        primaryTypographyProps={{ variant: "body2" }}
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </Box>
          )}
        </Stack>
      </DialogContent>
      <DialogActions className={classes.buttons}>
        <Button variant="outlined" onClick={handleClose}>
          {strings.common.cancel}
        </Button>
        {!hasResult && (
          <Button
            variant="contained"
            onClick={() => mutation.mutate()}
            disabled={!canImport}
          >
            {mutation.isPending ? strings.import.importing : strings.import.importButton}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
