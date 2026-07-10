import { isDemoMode } from "../demo/config";
import { demoApi, demoFetchSession } from "../demo/api";
import type {
  AppConfigResponse,
  CostReportDetailResponse,
  CostReportResponse,
  DashboardResponse,
  FleetRecordListResponse,
  HealthResponse,
  MaintenanceRecord,
  MaintenanceRecordDetail,
  MovementCreatePayload,
  MovementListResponse,
  Part,
  PartCreatePayload,
  PartUpdatePayload,
  RecordCreatePayload,
  RecordListResponse,
  RecordUpdatePayload,
  Reminder,
  ReminderCreatePayload,
  ReminderUpdatePayload,
  ReminderWithVehicle,
  ServiceType,
  ServiceTypeCreatePayload,
  ServiceTypeUpdatePayload,
  StockMovement,
  Vehicle,
  VehicleBulkCreatePayload,
  VehicleBulkCreateResult,
  VehicleCreatePayload,
  VehicleDetail,
  VehicleTransferPayload,
  VehicleTransferResult,
  VehicleUpdatePayload,
  MaintenanceSyncResult,
  ImportResult,
} from "./types";
import type { AuthUser } from "./auth";
import { ApiError } from "./errors";

export type { AuthUser } from "./auth";
export { ApiError } from "./errors";

const BASE_URL = "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    // Sends our maint_session cookie set by POST /auth/login.
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // non-JSON error body; keep statusText
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function fetchSession(): Promise<AuthUser | null> {
  if (isDemoMode) {
    return demoFetchSession();
  }
  try {
    return await request<AuthUser>("/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }
    throw error;
  }
}

const realApi = {
  login: (email: string, password: string) =>
    request<AuthUser>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  getMe: () => request<AuthUser>("/auth/me"),

  getHealth: () => request<HealthResponse>("/health"),
  getConfig: () => request<AppConfigResponse>("/config"),

  getVehicles: () => request<Vehicle[]>("/vehicles"),
  getVehicle: (id: number) => request<VehicleDetail>(`/vehicles/${id}`),
  createVehicle: (payload: VehicleCreatePayload) =>
    request<Vehicle>("/vehicles", { method: "POST", body: JSON.stringify(payload) }),
  bulkCreateVehicles: (payload: VehicleBulkCreatePayload) =>
    request<VehicleBulkCreateResult>("/vehicles/bulk", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateVehicle: (id: number, payload: VehicleUpdatePayload) =>
    request<Vehicle>(`/vehicles/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  archiveVehicle: (id: number) =>
    request<void>(`/vehicles/${id}`, { method: "DELETE" }),
  transferTracker: (id: number, payload: VehicleTransferPayload) =>
    request<VehicleTransferResult>(`/vehicles/${id}/transfer`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  syncOdometer: (id: number) =>
    request<Vehicle>(`/vehicles/${id}/sync-odometer`, { method: "POST" }),
  syncMaintenance: (id: number) =>
    request<MaintenanceSyncResult>(`/vehicles/${id}/sync-maintenance`, {
      method: "POST",
    }),
  getLogServiceTypes: (vehicleId: number) =>
    request<ServiceType[]>(`/vehicles/${vehicleId}/log-service-types`),

  getRecords: (vehicleId: number, limit = 20, offset = 0) =>
    request<RecordListResponse>(
      `/vehicles/${vehicleId}/records?limit=${limit}&offset=${offset}`,
    ),
  getAllRecords: (limit = 20, offset = 0) =>
    request<FleetRecordListResponse>(`/records?limit=${limit}&offset=${offset}`),
  createRecord: (vehicleId: number, payload: RecordCreatePayload) =>
    request<MaintenanceRecord>(`/vehicles/${vehicleId}/records`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateRecord: (recordId: number, payload: RecordUpdatePayload) =>
    request<MaintenanceRecord>(`/records/${recordId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  getRecord: (recordId: number) =>
    request<MaintenanceRecordDetail>(`/records/${recordId}`),
  deleteRecord: (recordId: number) =>
    request<void>(`/records/${recordId}`, { method: "DELETE" }),
  importRecords: (rows: Record<string, string>[]) =>
    request<ImportResult>("/records/import", {
      method: "POST",
      body: JSON.stringify({ rows }),
    }),

  getServiceTypes: () => request<ServiceType[]>("/service-types"),
  createServiceType: (payload: ServiceTypeCreatePayload) =>
    request<ServiceType>("/service-types", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateServiceType: (id: number, payload: ServiceTypeUpdatePayload) =>
    request<ServiceType>(`/service-types/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteServiceType: (serviceTypeId: number) =>
    request<void>(`/service-types/${serviceTypeId}`, { method: "DELETE" }),
  getServiceTypeRecords: (serviceTypeId: number, limit = 20, offset = 0) =>
    request<FleetRecordListResponse>(
      `/service-types/${serviceTypeId}/records?limit=${limit}&offset=${offset}`,
    ),
  importServiceTypes: (rows: Record<string, string>[]) =>
    request<ImportResult>("/service-types/import", {
      method: "POST",
      body: JSON.stringify({ rows }),
    }),

  getParts: (includeArchived = false) =>
    request<Part[]>(`/parts?include_archived=${includeArchived}`),
  createPart: (payload: PartCreatePayload) =>
    request<Part>("/parts", { method: "POST", body: JSON.stringify(payload) }),
  updatePart: (partId: number, payload: PartUpdatePayload) =>
    request<Part>(`/parts/${partId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  archivePart: (partId: number) =>
    request<void>(`/parts/${partId}`, { method: "DELETE" }),
  getMovements: (partId: number, limit = 20, offset = 0) =>
    request<MovementListResponse>(
      `/parts/${partId}/movements?limit=${limit}&offset=${offset}`,
    ),
  createMovement: (partId: number, payload: MovementCreatePayload) =>
    request<StockMovement>(`/parts/${partId}/movements`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getLowStock: () => request<Part[]>("/stock/low"),
  importParts: (rows: Record<string, string>[]) =>
    request<ImportResult>("/parts/import", {
      method: "POST",
      body: JSON.stringify({ rows }),
    }),

  getReminders: (vehicleId: number) =>
    request<Reminder[]>(`/vehicles/${vehicleId}/reminders`),
  getAllReminders: () => request<ReminderWithVehicle[]>("/reminders"),
  createReminder: (vehicleId: number, payload: ReminderCreatePayload) =>
    request<Reminder>(`/vehicles/${vehicleId}/reminders`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateReminder: (reminderId: number, payload: ReminderUpdatePayload) =>
    request<Reminder>(`/reminders/${reminderId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteReminder: (reminderId: number) =>
    request<void>(`/reminders/${reminderId}`, { method: "DELETE" }),

  getCostReport: (from: string, to: string, vehicleId?: number) => {
    const params = new URLSearchParams({ from, to });
    if (vehicleId !== undefined) params.set("vehicle_id", String(vehicleId));
    return request<CostReportResponse>(`/reports/costs?${params}`);
  },
  getCostReportDetail: (vehicleId: number, year: number, month: number) =>
    request<CostReportDetailResponse>(
      `/reports/costs/detail?vehicle_id=${vehicleId}&year=${year}&month=${month}`,
    ),
  getDashboard: () => request<DashboardResponse>("/reports/dashboard"),
  exportRecordsUrl: (from: string, to: string, vehicleId?: number) => {
    const params = new URLSearchParams({ from, to });
    if (vehicleId !== undefined) params.set("vehicle_id", String(vehicleId));
    return `${BASE_URL}/reports/records/export?${params}`;
  },
  downloadRecordsExport: async (from: string, to: string, vehicleId?: number) => {
    const response = await fetch(realApi.exportRecordsUrl(from, to, vehicleId), {
      credentials: "include",
    });
    if (!response.ok) {
      throw new ApiError(response.status, `Export failed (${response.status})`);
    }
    const blob = await response.blob();
    const header = response.headers.get("Content-Disposition");
    const match = header ? /filename="?([^";\n]+)"?/i.exec(header) : null;
    return {
      blob,
      filename: match?.[1] ?? `maintenance-records-${from}-${to}.csv`,
    };
  },
};

export const api = isDemoMode ? demoApi : realApi;
