import {
  Chip,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import type { Part } from "../api/types";
import { formatCost } from "../format";
import { useSettingsStyles } from "../styles/useSettingsStyles";
import { useCurrency } from "../hooks/useCurrency";
import { useStrings } from "../hooks/useLocale";
import { TablePanel } from "./TablePanel";

interface Props {
  parts: Part[];
  onRowClick?: (part: Part) => void;
}

export function PartsTable({ parts, onRowClick }: Props) {
  const strings = useStrings();
  const { currency } = useCurrency();
  const { classes } = useSettingsStyles();

  return (
    <TablePanel>
      <Table className={classes.table} size="small">
        <TableHead>
          <TableRow>
            <TableCell className={classes.hideOnMobile}>{strings.parts.sku}</TableCell>
            <TableCell>{strings.parts.name}</TableCell>
            <TableCell>{strings.parts.currentStock}</TableCell>
            <TableCell className={classes.hideOnMobile}>{strings.parts.minStock}</TableCell>
            <TableCell className={classes.hideOnMobile}>{strings.parts.unitCost}</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {parts.map((part) => (
            <TableRow
              key={part.id}
              hover={!!onRowClick}
              sx={{ cursor: onRowClick ? "pointer" : undefined }}
              onClick={() => onRowClick?.(part)}
            >
              <TableCell className={classes.hideOnMobile}>
                {part.sku ?? strings.common.notAvailable}
              </TableCell>
              <TableCell>{part.name}</TableCell>
              <TableCell>
                <Typography
                  component="span"
                  variant="body2"
                  color={part.low_stock ? "error" : undefined}
                  fontWeight={part.low_stock ? 700 : undefined}
                >
                  {Number(part.current_stock).toLocaleString("en-GB")} {part.unit}
                </Typography>{" "}
                {part.low_stock && (
                  <Chip label={strings.parts.lowStockBadge} color="error" size="small" />
                )}
              </TableCell>
              <TableCell className={classes.hideOnMobile}>
                {Number(part.min_stock).toLocaleString("en-GB")} {part.unit}
              </TableCell>
              <TableCell className={classes.hideOnMobile}>
                {formatCost(part.unit_cost, currency)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TablePanel>
  );
}
