import { useQuery } from "@tanstack/react-query";
import { fetchSession } from "../api/client";
import AppMenu from "./AppMenu";

export function useAppMenu({ onLogout }: { onLogout: () => void }) {
  const { data: user } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: fetchSession,
  });

  return (
    <AppMenu
      userName={user?.name || user?.email}
      onLogout={onLogout}
    />
  );
}
