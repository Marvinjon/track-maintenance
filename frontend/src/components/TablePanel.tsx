import { TableContainer } from "@mui/material";
import { useSettingsStyles } from "../styles/useSettingsStyles";

export function TablePanel({ children }: { children: React.ReactNode }) {
  const { classes } = useSettingsStyles();
  return <TableContainer className={classes.tableWrap}>{children}</TableContainer>;
}
