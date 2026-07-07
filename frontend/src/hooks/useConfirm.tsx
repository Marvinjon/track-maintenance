import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { ConfirmSnackbar } from "../components/ConfirmSnackbar";
import { useStrings } from "./useLocale";

interface ConfirmRequest {
  message: string;
  confirmLabel: string;
  resolve: (confirmed: boolean) => void;
}

type ConfirmFn = (message: string, confirmLabel?: string) => Promise<boolean>;

const ConfirmContext = createContext<ConfirmFn | null>(null);

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const strings = useStrings();
  const [request, setRequest] = useState<ConfirmRequest | null>(null);
  const requestRef = useRef<ConfirmRequest | null>(null);

  const finish = useCallback((confirmed: boolean) => {
    const current = requestRef.current;
    if (!current) return;
    requestRef.current = null;
    setRequest(null);
    current.resolve(confirmed);
  }, []);

  const confirm = useCallback<ConfirmFn>((message, confirmLabel) => {
    return new Promise<boolean>((resolve) => {
      if (requestRef.current) {
        requestRef.current.resolve(false);
      }
      const next: ConfirmRequest = {
        message,
        confirmLabel: confirmLabel ?? strings.common.delete,
        resolve,
      };
      requestRef.current = next;
      setRequest(next);
    });
  }, [strings.common.delete]);

  const value = useMemo(() => confirm, [confirm]);

  return (
    <ConfirmContext.Provider value={value}>
      {children}
      <ConfirmSnackbar
        open={request !== null}
        message={request?.message ?? ""}
        confirmLabel={request?.confirmLabel ?? strings.common.delete}
        onConfirm={() => finish(true)}
        onClose={() => finish(false)}
      />
    </ConfirmContext.Provider>
  );
}

export function useConfirm(): ConfirmFn {
  const confirm = useContext(ConfirmContext);
  if (!confirm) {
    throw new Error("useConfirm must be used within ConfirmProvider");
  }
  return confirm;
}
