import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export function useTraccarPublicUrl(): string | null {
  const { data } = useQuery({
    queryKey: ["app-config"],
    queryFn: api.getConfig,
    staleTime: 300_000,
  });
  return data?.traccar_public_url ?? null;
}

export function traccarDeviceUrl(publicUrl: string, deviceId: number): string {
  const base = publicUrl.replace(/\/$/, "");
  return `${base}/reports/summary?deviceId=${deviceId}`;
}
