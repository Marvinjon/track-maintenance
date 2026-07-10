import { useQuery } from "@tanstack/react-query";
import { fetchSession, type AuthUser } from "../api/client";

export function isTraccarReadOnly(user: AuthUser | null | undefined): boolean {
  return Boolean(user?.readonly || user?.device_readonly);
}

export function useAuthUser() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: fetchSession,
    staleTime: Infinity,
  });
}
