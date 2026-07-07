import CloseIcon from "@mui/icons-material/Close";
import {
  Box,
  Button,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import type { Part } from "../api/types";
import { formatCost } from "../format";
import { DEFAULT_CURRENCY } from "../hooks/useCurrency";
import { useStrings } from "../hooks/useLocale";

export interface PartRow {
  partId: string;
  quantity: string;
}

interface Props {
  rows: PartRow[];
  setRows: (rows: PartRow[]) => void;
  parts: Part[];
  /** Extra stock per part id, e.g. quantities already on the record being edited. */
  stockBonus?: Record<string, number>;
  currency?: string;
}

export function PartsPicker({
  rows,
  setRows,
  parts,
  stockBonus = {},
  currency = DEFAULT_CURRENCY,
}: Props) {
  const strings = useStrings();
  const byId = new Map(parts.map((p) => [String(p.id), p]));

  const update = (index: number, patch: Partial<PartRow>) => {
    setRows(rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  };

  const lineCost = (part: Part | undefined, quantity: string): number | null => {
    if (!part?.unit_cost || quantity === "" || Number(quantity) <= 0) return null;
    return Number(part.unit_cost) * Number(quantity);
  };

  const estimatedTotal = rows.reduce((sum, row) => {
    const part = row.partId ? byId.get(row.partId) : undefined;
    return sum + (lineCost(part, row.quantity) ?? 0);
  }, 0);

  return (
    <Stack spacing={1}>
      <Typography variant="subtitle2">{strings.logService.partsUsed}</Typography>
      {rows.map((row, index) => {
        const part = row.partId ? byId.get(row.partId) : undefined;
        const available =
          part !== undefined
            ? Number(part.current_stock) + (stockBonus[row.partId] ?? 0)
            : 0;
        const exceeds =
          part !== undefined &&
          row.quantity !== "" &&
          Number(row.quantity) > available;
        const rowLineCost = lineCost(part, row.quantity);

        return (
          <Box key={index}>
            <Box
              sx={{
                display: "grid",
                gap: 1,
                alignItems: "flex-end",
                gridTemplateColumns: {
                  xs: "1fr",
                  sm: "minmax(0, 1fr) 88px 100px 100px auto",
                },
              }}
            >
              <FormControl fullWidth size="small">
                <InputLabel>{strings.logService.partPlaceholder}</InputLabel>
                <Select
                  label={strings.logService.partPlaceholder}
                  value={row.partId}
                  onChange={(e) => update(index, { partId: e.target.value })}
                >
                  {parts.map((p) => (
                    <MenuItem key={p.id} value={String(p.id)}>
                      {`${p.name}${p.sku ? ` (${p.sku})` : ""} — ${strings.logService.inStock(
                        `${Number(p.current_stock).toLocaleString("en-GB")} ${p.unit}`,
                      )}`}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                label={strings.logService.quantity}
                type="number"
                value={row.quantity}
                onChange={(e) => update(index, { quantity: e.target.value })}
                size="small"
                inputProps={{ min: 0.01, step: 0.01 }}
              />
              <TextField
                label={strings.parts.unitCost}
                value={
                  part?.unit_cost
                    ? formatCost(part.unit_cost, currency).replace(` ${currency}`, "")
                    : strings.common.notAvailable
                }
                size="small"
                InputProps={{ readOnly: true }}
              />
              <TextField
                label={strings.reports.lineCost}
                value={
                  rowLineCost !== null
                    ? formatCost(String(rowLineCost), currency).replace(` ${currency}`, "")
                    : strings.common.notAvailable
                }
                size="small"
                InputProps={{ readOnly: true }}
              />
              <IconButton
                size="small"
                color="error"
                aria-label={strings.logService.removePart}
                onClick={() => setRows(rows.filter((_, i) => i !== index))}
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            </Box>
            {exceeds && (
              <Typography variant="caption" color="warning.main" sx={{ mt: 0.5, display: "block" }}>
                {strings.logService.exceedsStock}
              </Typography>
            )}
          </Box>
        );
      })}
      <Button
        variant="outlined"
        size="small"
        onClick={() => setRows([...rows, { partId: "", quantity: "1" }])}
      >
        {strings.logService.addPart}
      </Button>
      {estimatedTotal > 0 && (
        <Typography variant="body2" color="text.secondary">
          {strings.logService.estimatedPartsCost}: {formatCost(String(estimatedTotal), currency)}
        </Typography>
      )}
    </Stack>
  );
}

export function validPartRows(rows: PartRow[]): PartRow[] {
  return rows.filter(
    (row) => row.partId !== "" && row.quantity !== "" && Number(row.quantity) > 0,
  );
}
