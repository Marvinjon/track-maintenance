import { api } from "../api/client";
import type {
  CostReportDetailResponse,
  CostReportResponse,
  MaintenanceRecord,
  MaintenanceRecordWithVehicle,
  MonthlyCostRow,
  Part,
  Reminder,
  ReminderWithVehicle,
  ServiceType,
  StockMovement,
  Vehicle,
} from "../api/types";
import { formatKm } from "../format";
import type { Locale, Strings } from "../i18n";
import { localeTag } from "../i18n";
import type { ExportSheet } from "./tableExport";

function monthLabel(locale: Locale, year: number, month: number): string {
  return new Date(year, month - 1, 1).toLocaleDateString(localeTag(locale), {
    month: "long",
    year: "numeric",
  });
}

function vehicleLabel(
  s: Strings,
  plate: string | null | undefined,
  device: string | null | undefined,
): string {
  return plate?.trim() || device?.trim() || s.common.notAvailable;
}

export function vehiclesExportSheet(s: Strings, vehicles: Vehicle[]): ExportSheet {
  const NA = s.common.notAvailable;
  return {
    name: s.nav.vehicles,
    headers: [
      s.vehicles.plate,
      s.vehicles.device,
      s.vehicles.makeModel,
      s.vehicles.odometer,
      s.vehicles.reminderStatus,
      s.vehicles.lastService,
      s.export.tracked,
    ],
    rows: vehicles.map((v) => [
      v.registered ? v.plate || NA : s.vehicles.notRegistered,
      v.device_name || NA,
      [v.make, v.model].filter(Boolean).join(" ") || NA,
      v.registered ? formatKm(v.odometer_km_cached) : NA,
      v.registered ? v.reminder_status || NA : NA,
      v.last_service_date || s.common.never,
      v.registered ? s.common.yes : s.common.no,
    ]),
  };
}

export function remindersExportSheet(s: Strings, reminders: ReminderWithVehicle[]): ExportSheet {
  const NA = s.common.notAvailable;
  return {
    name: s.nav.upcomingMaintenance,
    headers: [
      s.reminders.vehicle,
      s.reminders.serviceType,
      s.reminders.intervalKm,
      s.reminders.intervalDays,
      s.reminders.intervalHours,
      s.reminders.lastService,
      s.reminders.status,
      s.reminders.syncError,
    ],
    rows: reminders.map((r) => [
      vehicleLabel(s, r.vehicle_plate, r.vehicle_device_name),
      r.service_type_name || NA,
      r.interval_km ?? NA,
      r.interval_days ?? NA,
      r.interval_hours ?? NA,
      r.last_service_date || s.common.never,
      r.status,
      r.sync_error ? s.reminders.syncError : "",
    ]),
  };
}

export function vehicleRemindersExportSheet(s: Strings, reminders: Reminder[]): ExportSheet {
  const NA = s.common.notAvailable;
  return {
    name: s.vehicleDetail.tabs.reminders,
    headers: [
      s.reminders.serviceType,
      s.reminders.intervalKm,
      s.reminders.intervalDays,
      s.reminders.intervalHours,
      s.reminders.lastService,
      s.reminders.status,
      s.reminders.syncError,
    ],
    rows: reminders.map((r) => [
      r.service_type_name || NA,
      r.interval_km ?? NA,
      r.interval_days ?? NA,
      r.interval_hours ?? NA,
      r.last_service_date || s.common.never,
      r.status,
      r.sync_error ? s.reminders.syncError : "",
    ]),
  };
}

export function partsExportSheet(s: Strings, parts: Part[]): ExportSheet {
  const NA = s.common.notAvailable;
  return {
    name: s.nav.parts,
    headers: [
      s.parts.sku,
      s.parts.name,
      s.parts.unit,
      s.parts.currentStock,
      s.parts.minStock,
      s.parts.unitCost,
      s.parts.lowStockBadge,
    ],
    rows: parts.map((p) => [
      p.sku || NA,
      p.name,
      p.unit,
      Number(p.current_stock),
      Number(p.min_stock),
      p.unit_cost ? Number(p.unit_cost) : NA,
      p.low_stock ? s.parts.lowStockBadge : "",
    ]),
  };
}

export function serviceTypesExportSheet(s: Strings, types: ServiceType[]): ExportSheet {
  const NA = s.common.notAvailable;
  return {
    name: s.nav.serviceTypes,
    headers: [
      s.serviceTypes.name,
      s.serviceTypes.defaultIntervalKm,
      s.serviceTypes.defaultIntervalDays,
    ],
    rows: types.map((t) => [
      t.name,
      t.default_interval_km ?? NA,
      t.default_interval_days ?? NA,
    ]),
  };
}

export function recordsExportSheet(
  s: Strings,
  records: MaintenanceRecordWithVehicle[],
): ExportSheet {
  const NA = s.common.notAvailable;
  return {
    name: s.nav.services,
    headers: [
      s.reminders.vehicle,
      s.records.date,
      s.records.serviceType,
      s.records.odometerKm,
      s.records.cost,
      s.records.performedBy,
      s.records.notes,
    ],
    rows: records.map((r) => [
      vehicleLabel(s, r.vehicle_plate, r.vehicle_device_name),
      r.performed_at,
      r.service_type_name || NA,
      r.odometer_km ? Number(r.odometer_km) : NA,
      r.cost ? Number(r.cost) : NA,
      r.performed_by || NA,
      r.notes || NA,
    ]),
  };
}

export function movementsExportSheet(
  s: Strings,
  movements: StockMovement[],
  partName: string,
): ExportSheet {
  const NA = s.common.notAvailable;
  return {
    name: s.ledger.title,
    headers: [
      s.parts.name,
      s.ledger.date,
      s.ledger.quantity,
      s.ledger.reason,
      s.ledger.note,
      s.ledger.record,
    ],
    rows: movements.map((m) => [
      partName,
      m.created_at.slice(0, 10),
      Number(m.quantity),
      s.ledger.reasonLabels[m.reason],
      m.note || NA,
      m.maintenance_record_id ?? NA,
    ]),
  };
}

export function costReportSummarySheet(
  s: Strings,
  locale: Locale,
  data: CostReportResponse,
): ExportSheet {
  const NA = s.common.notAvailable;
  return {
    name: s.reports.title,
    headers: [
      s.reports.period,
      s.reminders.vehicle,
      s.reports.laborCost,
      s.reports.partsCost,
      s.reports.totalCost,
      s.reports.costPerKm,
      s.reports.costPerHour,
      s.reports.records,
    ],
    rows: data.rows.map((row: MonthlyCostRow) => [
      monthLabel(locale, row.year, row.month),
      vehicleLabel(s, row.vehicle_plate, row.vehicle_device_name),
      Number(row.labor_cost),
      Number(row.parts_cost),
      Number(row.total_cost),
      row.cost_per_km ? Number(row.cost_per_km) : NA,
      row.cost_per_hour ? Number(row.cost_per_hour) : NA,
      row.record_count,
    ]),
  };
}

export function costReportDetailSheets(
  s: Strings,
  locale: Locale,
  data: CostReportDetailResponse,
): ExportSheet[] {
  const NA = s.common.notAvailable;
  const vehicle = vehicleLabel(s, data.vehicle_plate, data.vehicle_device_name);
  const period = monthLabel(locale, data.year, data.month);
  const numberLocale = localeTag(locale);

  const summary: ExportSheet = {
    name: s.export.summary,
    headers: [
      s.reports.period,
      s.reminders.vehicle,
      s.reports.laborCost,
      s.reports.partsCost,
      s.reports.totalCost,
    ],
    rows: [[period, vehicle, Number(data.labor_cost), Number(data.parts_cost), Number(data.total_cost)]],
  };

  const byType: ExportSheet = {
    name: s.reports.byServiceType,
    headers: [
      s.records.serviceType,
      s.reports.records,
      s.reports.laborCost,
      s.reports.partsCost,
      s.reports.totalCost,
    ],
    rows: data.service_type_breakdown.map((row) => [
      row.service_type_name,
      row.record_count,
      Number(row.labor_cost),
      Number(row.parts_cost),
      Number(row.total_cost),
    ]),
  };

  const partsSummary: ExportSheet = {
    name: s.reports.partsInventory,
    headers: [s.parts.name, s.parts.sku, s.ledger.quantity, s.reports.totalCost],
    rows: data.parts_summary.map((p) => [
      p.part_name,
      p.sku || NA,
      `${Number(p.total_quantity).toLocaleString(numberLocale)} ${p.unit}`,
      Number(p.total_cost),
    ]),
  };

  const services: ExportSheet = {
    name: s.reports.services,
    headers: [
      s.records.date,
      s.records.serviceType,
      s.records.odometerKm,
      s.records.performedBy,
      s.reports.laborCost,
      s.reports.partsCost,
      s.reports.totalCost,
      s.parts.name,
      s.parts.sku,
      s.ledger.quantity,
      s.reports.lineCost,
      s.records.notes,
    ],
    rows: data.records.flatMap((record) => {
      const base = [
        record.performed_at,
        record.service_type_name,
        record.odometer_km ? Number(record.odometer_km) : NA,
        record.performed_by || NA,
        record.labor_cost ? Number(record.labor_cost) : 0,
        Number(record.parts_cost),
        Number(record.total_cost),
      ];
      if (record.parts.length === 0) {
        return [[...base, NA, NA, NA, NA, record.notes || NA]];
      }
      return record.parts.map((part, index) => [
        ...base,
        part.part_name,
        part.sku || NA,
        `${Number(part.quantity).toLocaleString(numberLocale)} ${part.unit}`,
        Number(part.line_cost),
        index === 0 ? record.notes || NA : "",
      ]);
    }),
  };

  return [summary, byType, partsSummary, services];
}

export async function fetchAllRecords(): Promise<MaintenanceRecordWithVehicle[]> {
  const limit = 100;
  let offset = 0;
  const items: MaintenanceRecordWithVehicle[] = [];
  while (true) {
    const page = await api.getAllRecords(limit, offset);
    items.push(...page.items);
    if (items.length >= page.total) break;
    offset += limit;
  }
  return items;
}

export async function fetchVehicleRecords(vehicleId: number): Promise<MaintenanceRecord[]> {
  const limit = 100;
  let offset = 0;
  const items: MaintenanceRecord[] = [];
  while (true) {
    const page = await api.getRecords(vehicleId, limit, offset);
    items.push(...page.items);
    if (items.length >= page.total) break;
    offset += limit;
  }
  return items;
}

export function vehicleRecordsExportSheet(
  s: Strings,
  records: MaintenanceRecord[],
  vehicle: string,
): ExportSheet {
  const NA = s.common.notAvailable;
  return {
    name: s.vehicleDetail.tabs.records,
    headers: [
      s.reminders.vehicle,
      s.records.date,
      s.records.serviceType,
      s.records.odometerKm,
      s.records.cost,
      s.records.performedBy,
      s.records.notes,
    ],
    rows: records.map((r) => [
      vehicle,
      r.performed_at,
      r.service_type_name || NA,
      r.odometer_km ? Number(r.odometer_km) : NA,
      r.cost ? Number(r.cost) : NA,
      r.performed_by || NA,
      r.notes || NA,
    ]),
  };
}

export async function fetchAllMovements(partId: number): Promise<StockMovement[]> {
  const limit = 100;
  let offset = 0;
  const items: StockMovement[] = [];
  while (true) {
    const page = await api.getMovements(partId, limit, offset);
    items.push(...page.items);
    if (items.length >= page.total) break;
    offset += limit;
  }
  return items;
}

export async function fetchAllServiceTypeRecords(
  serviceTypeId: number,
): Promise<MaintenanceRecordWithVehicle[]> {
  const limit = 100;
  let offset = 0;
  const items: MaintenanceRecordWithVehicle[] = [];
  while (true) {
    const page = await api.getServiceTypeRecords(serviceTypeId, limit, offset);
    items.push(...page.items);
    if (items.length >= page.total) break;
    offset += limit;
  }
  return items;
}
