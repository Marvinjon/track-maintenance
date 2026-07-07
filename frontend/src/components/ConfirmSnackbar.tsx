import { Button, Portal, Snackbar } from "@mui/material";
import { makeStyles } from "tss-react/mui";

const SNACKBAR_DURATION_MS = 10_000;

const useStyles = makeStyles()((theme) => ({
  root: {
    [theme.breakpoints.down("md")]: {
      bottom: `calc(${theme.dimensions.bottomBarHeight}px + ${theme.spacing(1)})`,
    },
  },
  button: {
    height: "auto",
    marginTop: 0,
    marginBottom: 0,
  },
}));

interface Props {
  open: boolean;
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  onClose: () => void;
}

export function ConfirmSnackbar({ open, message, confirmLabel, onConfirm, onClose }: Props) {
  const { classes } = useStyles();

  return (
    <Portal>
      <Snackbar
        className={classes.root}
        open={open}
        autoHideDuration={SNACKBAR_DURATION_MS}
        onClose={(_, reason) => {
          if (reason === "clickaway") return;
          onClose();
        }}
        message={message}
        action={
          <Button size="small" className={classes.button} color="error" onClick={onConfirm}>
            {confirmLabel}
          </Button>
        }
      />
    </Portal>
  );
}
