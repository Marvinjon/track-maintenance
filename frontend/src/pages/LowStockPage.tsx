import { Alert, Box, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { PartsTable } from "../components/PartsTable";
import { TableExportButton } from "../components/TableExportButton";
import { partsExportSheet } from "../export/datasets";
import { useStrings } from "../hooks/useLocale";

export default function LowStockPage() {
  const strings = useStrings();
  const { data: parts, isLoading, isError } = useQuery({
    queryKey: ["low-stock"],
    queryFn: api.getLowStock,
  });

  if (isLoading) return <Typography>{strings.common.loading}</Typography>;
  if (isError || !parts) return <Alert severity="error">{strings.common.error}</Alert>;

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2, flexWrap: "wrap", gap: 1 }}>
        <Typography variant="h5">{strings.lowStock.title}</Typography>
        <TableExportButton
          filename="low-stock"
          sheets={() => [partsExportSheet(strings, parts)]}
          disabled={parts.length === 0}
        />
      </Box>
      {parts.length === 0 ? (
        <Typography color="text.secondary">{strings.lowStock.empty}</Typography>
      ) : (
        <PartsTable parts={parts} />
      )}
    </>
  );
}
