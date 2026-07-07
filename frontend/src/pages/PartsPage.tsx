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
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import type { Part } from "../api/types";
import { PartDrawer } from "../components/PartDrawer";
import { PartsTable } from "../components/PartsTable";
import { TableExportButton } from "../components/TableExportButton";
import { TableImportButton } from "../components/TableImportButton";
import { partsExportSheet } from "../export/datasets";
import {
  PARTS_IMPORT_EXAMPLE,
  PARTS_IMPORT_HEADERS,
} from "../export/importTemplates";
import { useSettingsStyles } from "../styles/useSettingsStyles";
import { useStrings } from "../hooks/useLocale";

function NewPartDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const strings = useStrings();
  const queryClient = useQueryClient();
  const { classes } = useSettingsStyles();
  const [name, setName] = useState("");
  const [sku, setSku] = useState("");
  const [unit, setUnit] = useState("pcs");
  const [minStock, setMinStock] = useState("");
  const [unitCost, setUnitCost] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      api.createPart({
        name,
        sku: sku || undefined,
        unit: unit || undefined,
        min_stock: minStock === "" ? undefined : minStock,
        unit_cost: unitCost === "" ? undefined : unitCost,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["parts"] });
      queryClient.invalidateQueries({ queryKey: ["low-stock"] });
      setName("");
      setSku("");
      setUnitCost("");
      setMinStock("");
      onClose();
    },
  });

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{strings.parts.newPartTitle}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <TextField
            label={strings.parts.name}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            fullWidth
            size="small"
          />
          <TextField
            label={strings.parts.sku}
            value={sku}
            onChange={(e) => setSku(e.target.value)}
            fullWidth
            size="small"
          />
          <TextField
            label={strings.parts.unit}
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
            fullWidth
            size="small"
          />
          <TextField
            label={strings.parts.minStock}
            type="number"
            value={minStock}
            onChange={(e) => setMinStock(e.target.value)}
            inputProps={{ min: 0, step: 0.01 }}
            fullWidth
            size="small"
          />
          <TextField
            label={strings.parts.unitCost}
            type="number"
            value={unitCost}
            onChange={(e) => setUnitCost(e.target.value)}
            inputProps={{ min: 0 }}
            fullWidth
            size="small"
            InputProps={{
              endAdornment: ` ${strings.logService.currency}`,
            }}
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
          {strings.parts.create}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default function PartsPage() {
  const strings = useStrings();
  const { classes } = useSettingsStyles();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const { data: parts, isLoading, isError } = useQuery({
    queryKey: ["parts"],
    queryFn: () => api.getParts(),
  });

  const selected: Part | null = parts?.find((p) => p.id === selectedId) ?? null;

  if (isLoading) return <Typography>{strings.common.loading}</Typography>;
  if (isError || !parts) return <Alert severity="error">{strings.common.error}</Alert>;

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2, flexWrap: "wrap", gap: 1 }}>
        <Typography variant="h5">{strings.parts.title}</Typography>
        <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
          <TableImportButton
            title={strings.import.partsTitle}
            templateFilename="parts-import-template"
            templateHeaders={PARTS_IMPORT_HEADERS}
            templateExampleRow={PARTS_IMPORT_EXAMPLE}
            onImport={api.importParts}
            invalidateQueries={[["parts"], ["low-stock"]]}
          />
          <TableExportButton
            filename="parts"
            sheets={() => [partsExportSheet(strings, parts)]}
            disabled={parts.length === 0}
          />
        </Box>
      </Box>

      {parts.length === 0 ? (
        <Typography color="text.secondary">{strings.parts.empty}</Typography>
      ) : (
        <PartsTable parts={parts} onRowClick={(part) => setSelectedId(part.id)} />
      )}

      <Fab
        color="primary"
        aria-label={strings.parts.addPart}
        className={classes.fab}
        onClick={() => setDialogOpen(true)}
      >
        <AddIcon />
      </Fab>

      <NewPartDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
      <PartDrawer part={selected} onClose={() => setSelectedId(null)} />
    </>
  );
}
