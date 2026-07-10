import RefreshIcon from "@mui/icons-material/Refresh";
import { Alert, Box, Button } from "@mui/material";
import { useQueryClient } from "@tanstack/react-query";
import { resetDemoStore } from "./api";
import { useStrings } from "../hooks/useLocale";

export function DemoBanner() {
  const strings = useStrings();
  const queryClient = useQueryClient();

  const handleReset = () => {
    resetDemoStore();
    void queryClient.invalidateQueries();
  };

  return (
    <Box sx={{ mb: 2 }}>
      <Alert
        severity="info"
        action={
          <Button
            color="inherit"
            size="small"
            startIcon={<RefreshIcon />}
            onClick={handleReset}
          >
            {strings.demo.reset}
          </Button>
        }
      >
        {strings.demo.banner}
      </Alert>
    </Box>
  );
}
