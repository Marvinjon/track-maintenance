import type { AuthUser } from "../api/auth";
import { DEMO_USER } from "./config";
import { demoStore, resetDemoStore } from "./store";

export async function demoFetchSession(): Promise<AuthUser> {
  return demoStore.getMe();
}

export const demoApi = {
  login: (_email: string, _password: string) => demoStore.login(),
  logout: () => demoStore.logout(),
  getMe: () => demoStore.getMe(),

  getHealth: () => demoStore.getHealth(),
  getConfig: () => demoStore.getConfig(),

  getVehicles: () => demoStore.getVehicles(),
  getVehicle: (id: number) => demoStore.getVehicle(id),
  createVehicle: (payload: Parameters<typeof demoStore.createVehicle>[0]) =>
    demoStore.createVehicle(payload),
  bulkCreateVehicles: (payload: Parameters<typeof demoStore.bulkCreateVehicles>[0]) =>
    demoStore.bulkCreateVehicles(payload),
  updateVehicle: (id: number, payload: Parameters<typeof demoStore.updateVehicle>[1]) =>
    demoStore.updateVehicle(id, payload),
  archiveVehicle: (id: number) => demoStore.archiveVehicle(id),
  transferTracker: (id: number, payload: Parameters<typeof demoStore.transferTracker>[1]) =>
    demoStore.transferTracker(id, payload),
  syncOdometer: (id: number) => demoStore.syncOdometer(id),
  syncMaintenance: (id: number) => demoStore.syncMaintenance(id),
  getLogServiceTypes: (vehicleId: number) => demoStore.getLogServiceTypes(vehicleId),

  getRecords: (vehicleId: number, limit = 20, offset = 0) =>
    demoStore.getRecords(vehicleId, limit, offset),
  getAllRecords: (limit = 20, offset = 0) => demoStore.getAllRecords(limit, offset),
  createRecord: (vehicleId: number, payload: Parameters<typeof demoStore.createRecord>[1]) =>
    demoStore.createRecord(vehicleId, payload),
  updateRecord: (recordId: number, payload: Parameters<typeof demoStore.updateRecord>[1]) =>
    demoStore.updateRecord(recordId, payload),
  getRecord: (recordId: number) => demoStore.getRecord(recordId),
  deleteRecord: (recordId: number) => demoStore.deleteRecord(recordId),
  importRecords: (_rows: Record<string, string>[]) => demoStore.importRecords(),

  getServiceTypes: () => demoStore.getServiceTypes(),
  createServiceType: (payload: Parameters<typeof demoStore.createServiceType>[0]) =>
    demoStore.createServiceType(payload),
  updateServiceType: (id: number, payload: Parameters<typeof demoStore.updateServiceType>[1]) =>
    demoStore.updateServiceType(id, payload),
  deleteServiceType: (serviceTypeId: number) => demoStore.deleteServiceType(serviceTypeId),
  getServiceTypeRecords: (serviceTypeId: number, limit = 20, offset = 0) =>
    demoStore.getServiceTypeRecords(serviceTypeId, limit, offset),
  importServiceTypes: (_rows: Record<string, string>[]) => demoStore.importServiceTypes(),

  getParts: (includeArchived = false) => demoStore.getParts(includeArchived),
  createPart: (payload: Parameters<typeof demoStore.createPart>[0]) =>
    demoStore.createPart(payload),
  updatePart: (partId: number, payload: Parameters<typeof demoStore.updatePart>[1]) =>
    demoStore.updatePart(partId, payload),
  archivePart: (partId: number) => demoStore.archivePart(partId),
  getMovements: (partId: number, limit = 20, offset = 0) =>
    demoStore.getMovements(partId, limit, offset),
  createMovement: (partId: number, payload: Parameters<typeof demoStore.createMovement>[1]) =>
    demoStore.createMovement(partId, payload),
  getLowStock: () => demoStore.getLowStock(),
  importParts: (_rows: Record<string, string>[]) => demoStore.importParts(),

  getReminders: (vehicleId: number) => demoStore.getReminders(vehicleId),
  getAllReminders: () => demoStore.getAllReminders(),
  createReminder: (vehicleId: number, payload: Parameters<typeof demoStore.createReminder>[1]) =>
    demoStore.createReminder(vehicleId, payload),
  updateReminder: (reminderId: number, payload: Parameters<typeof demoStore.updateReminder>[1]) =>
    demoStore.updateReminder(reminderId, payload),
  deleteReminder: (reminderId: number) => demoStore.deleteReminder(reminderId),

  getCostReport: (from: string, to: string, vehicleId?: number) =>
    demoStore.getCostReport(from, to, vehicleId),
  getCostReportDetail: (vehicleId: number, year: number, month: number) =>
    demoStore.getCostReportDetail(vehicleId, year, month),
  getDashboard: () => demoStore.getDashboard(),
  exportRecordsUrl: (from: string, to: string, vehicleId?: number) => {
    const params = new URLSearchParams({ from, to });
    if (vehicleId !== undefined) params.set("vehicle_id", String(vehicleId));
    return `/api/v1/reports/records/export?${params}`;
  },
  downloadRecordsExport: async (from: string, to: string, vehicleId?: number) => {
    const csv = demoStore.exportRecordsCsv(from, to, vehicleId);
    return {
      blob: new Blob([csv], { type: "text/csv" }),
      filename: `maintenance-records-${from}-${to}.csv`,
    };
  },
};

export { DEMO_USER, resetDemoStore };
