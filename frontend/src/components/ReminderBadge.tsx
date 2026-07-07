import type { ReminderStatus } from "../api/types";
import { Chip } from "@mui/material";
import { useStrings } from "../hooks/useLocale";

const COLORS: Record<ReminderStatus, "success" | "warning" | "error"> = {
  ok: "success",
  due_soon: "warning",
  overdue: "error",
};

export function ReminderBadge({ status }: { status: ReminderStatus | null }) {
  const strings = useStrings();
  if (status === null) {
    return <Chip label={strings.reminderBadge.none} size="small" variant="outlined" />;
  }
  return (
    <Chip
      label={strings.reminderBadge[status]}
      color={COLORS[status]}
      size="small"
    />
  );
}
