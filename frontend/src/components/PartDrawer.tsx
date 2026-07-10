import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  Box,
  Button,
  Chip,
  Divider,
  Drawer,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import type { MovementCreatePayload, Part } from "../api/types";
import { fetchAllMovements, movementsExportSheet } from "../export/datasets";
import { useConfirm } from "../hooks/useConfirm";
import { isTraccarReadOnly, useAuthUser } from "../hooks/useAuthUser";
import { useSettingsStyles } from "../styles/useSettingsStyles";
import { useStrings } from "../hooks/useLocale";
import { TableExportButton } from "./TableExportButton";
import { TablePanel } from "./TablePanel";

const MANUAL_REASONS: MovementCreatePayload["reason"][] = [
  "purchase",
  "adjustment",
  "return",
];

function AddMovementForm({ part }: { part: Part }) {
  const strings = useStrings();
  const queryClient = useQueryClient();
  const { classes } = useSettingsStyles();
  const [quantity, setQuantity] = useState("");
  const [reason, setReason] = useState<MovementCreatePayload["reason"]>("purchase");
  const [note, setNote] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      api.createMovement(part.id, {
        quantity,
        reason,
        note: note || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["movements", part.id] });
      queryClient.invalidateQueries({ queryKey: ["parts"] });
      queryClient.invalidateQueries({ queryKey: ["low-stock"] });
      setQuantity("");
      setNote("");
    },
  });

  return (
    <Stack spacing={1} className={classes.details}>
      <Typography variant="subtitle2">{strings.ledger.addMovement}</Typography>
      <Box className={classes.stackOnMobile}>
        <TextField
          label={strings.ledger.quantity}
          type="number"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          size="small"
          fullWidth
        />
        <FormControl fullWidth size="small">
          <InputLabel>{strings.ledger.reason}</InputLabel>
          <Select
            label={strings.ledger.reason}
            value={reason}
            onChange={(e) => setReason(e.target.value as MovementCreatePayload["reason"])}
          >
            {MANUAL_REASONS.map((r) => (
              <MenuItem key={r} value={r}>
                {strings.ledger.reasonLabels[r]}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>
      <TextField
        label={strings.ledger.note}
        value={note}
        onChange={(e) => setNote(e.target.value)}
        multiline
        minRows={1}
        size="small"
        fullWidth
      />
      <Button
        variant="contained"
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending || quantity === "" || Number(quantity) === 0}
      >
        {strings.ledger.submit}
      </Button>
    </Stack>
  );
}

export function PartDrawer({ part, onClose }: { part: Part | null; onClose: () => void }) {
  const strings = useStrings();
  const confirm = useConfirm();
  const queryClient = useQueryClient();
  const { data: authUser } = useAuthUser();
  const readOnly = isTraccarReadOnly(authUser);
  const [limit, setLimit] = useState(20);
  const { classes } = useSettingsStyles();
  const { data } = useQuery({
    queryKey: ["movements", part?.id, limit],
    queryFn: () => api.getMovements(part!.id, limit, 0),
    enabled: part !== null,
  });

  const archiveMutation = useMutation({
    mutationFn: () => api.archivePart(part!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["parts"] });
      queryClient.invalidateQueries({ queryKey: ["low-stock"] });
      onClose();
    },
  });

  return (
    <Drawer anchor="right" open={part !== null} onClose={onClose} PaperProps={{ sx: { width: 480 } }}>
      <Box sx={{ p: 2, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Typography variant="h6">
          {part ? `${part.name}${part.sku ? ` (${part.sku})` : ""}` : ""}
        </Typography>
        <IconButton onClick={onClose} aria-label={strings.common.cancel}>
          <CloseIcon />
        </IconButton>
      </Box>
      <Divider />
      {part && (
        <Box sx={{ p: 2 }}>
          <Stack spacing={2}>
            <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
              <Typography>
                {strings.parts.currentStock}:{" "}
                {Number(part.current_stock).toLocaleString("en-GB")} {part.unit}
              </Typography>
              {part.low_stock && (
                <Chip label={strings.parts.lowStockBadge} color="error" size="small" />
              )}
            </Box>

            <AddMovementForm part={part} />
            <Divider />

            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <Typography variant="subtitle2">{strings.ledger.title}</Typography>
              {data && data.total > 0 && (
                <TableExportButton
                  filename={`part-${part.id}-movements`}
                  sheets={async () => [
                    movementsExportSheet(strings, await fetchAllMovements(part.id), part.name),
                  ]}
                />
              )}
            </Box>
            {data && data.items.length === 0 && (
              <Typography color="text.secondary">{strings.ledger.empty}</Typography>
            )}
            {data && data.items.length > 0 && (
              <TablePanel>
                <Table size="small" className={classes.table}>
                  <TableHead>
                    <TableRow>
                      <TableCell>{strings.ledger.date}</TableCell>
                      <TableCell>{strings.ledger.quantity}</TableCell>
                      <TableCell>{strings.ledger.reason}</TableCell>
                      <TableCell className={classes.hideOnMobile}>{strings.ledger.note}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data.items.map((movement) => (
                      <TableRow key={movement.id}>
                        <TableCell>{movement.created_at.slice(0, 10)}</TableCell>
                        <TableCell>
                          <Typography
                            component="span"
                            variant="body2"
                            color={Number(movement.quantity) < 0 ? "error" : "success.main"}
                          >
                            {Number(movement.quantity) > 0 ? "+" : ""}
                            {Number(movement.quantity).toLocaleString("en-GB")}
                          </Typography>
                        </TableCell>
                        <TableCell>{strings.ledger.reasonLabels[movement.reason]}</TableCell>
                        <TableCell className={classes.hideOnMobile}>
                          <Typography variant="body2" noWrap sx={{ maxWidth: 160 }}>
                            {movement.note}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TablePanel>
            )}
            {data && data.total > data.items.length && (
              <Button variant="text" onClick={() => setLimit((l) => l + 20)}>
                {strings.ledger.loadMore}
              </Button>
            )}

            {!readOnly && (
              <Button
                variant="outlined"
                color="error"
                startIcon={<DeleteIcon />}
                disabled={archiveMutation.isPending}
                onClick={async () => {
                  if (await confirm(strings.parts.archiveConfirm)) {
                    archiveMutation.mutate();
                  }
                }}
                sx={{ alignSelf: "flex-start" }}
              >
                {strings.parts.archive}
              </Button>
            )}
          </Stack>
        </Box>
      )}
    </Drawer>
  );
}
