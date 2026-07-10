import { ApiError } from "../api/errors";
import type {
  AppConfigResponse,
  CostReportDetailResponse,
  CostReportResponse,
  DashboardResponse,
  FleetRecordListResponse,
  HealthResponse,
  ImportResult,
  MaintenanceRecord,
  MaintenanceRecordDetail,
  MaintenanceRecordWithVehicle,
  MaintenanceSyncResult,
  MovementCreatePayload,
  MovementListResponse,
  Part,
  PartCreatePayload,
  PartUpdatePayload,
  RecordChange,
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
} from "../api/types";
import { DEMO_USER } from "./config";
import { createInitialDemoState, type DemoState } from "./fixtures";

const DEMO_DELAY_MS = 80;

function delay(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, DEMO_DELAY_MS));
}

function clone<T>(value: T): T {
  return structuredClone(value);
}

function parseDecimal(value: string | number | null | undefined): number {
  if (value === null || value === undefined || value === "") return 0;
  return Number(value);
}

function formatDecimal(value: number, decimals = 1): string {
  return value.toFixed(decimals).replace(/\.0$/, "");
}

function paginate<T>(items: T[], limit: number, offset: number) {
  const slice = items.slice(offset, offset + limit);
  return { items: slice, total: items.length, limit, offset };
}

function monthKey(dateStr: string): string {
  return dateStr.slice(0, 7);
}

export class DemoStore {
  private state: DemoState;

  constructor() {
    this.state = createInitialDemoState();
  }

  reset(): void {
    this.state = createInitialDemoState();
  }

  private stockForPart(partId: number): number {
    return this.state.movements
      .filter((m) => m.part_id === partId)
      .reduce((sum, m) => sum + parseDecimal(m.quantity), 0);
  }

  private enrichPart(part: Omit<Part, "current_stock" | "low_stock">): Part {
    const stock = this.stockForPart(part.id);
    const minStock = parseDecimal(part.min_stock);
    return {
      ...part,
      current_stock: formatDecimal(stock),
      low_stock: stock < minStock,
    };
  }

  private deviceForVehicle(vehicle: Vehicle) {
    return {
      id: vehicle.traccar_device_id,
      name: vehicle.device_name ?? `Device ${vehicle.traccar_device_id}`,
      uniqueId: vehicle.device_unique_id ?? `IMEI-${vehicle.traccar_device_id}`,
      status: vehicle.device_status ?? "online",
    };
  }

  private activeVehicles(): Vehicle[] {
    return this.state.vehicles.filter((v) => !v.archived);
  }

  private vehicleById(id: number): Vehicle {
    const vehicle = this.state.vehicles.find((v) => v.id === id && !v.archived);
    if (!vehicle) throw new ApiError(404, "Vehicle not found");
    return vehicle;
  }

  private serviceTypeById(id: number): ServiceType {
    const st = this.state.serviceTypes.find((s) => s.id === id);
    if (!st) throw new ApiError(422, "Unknown service type");
    return st;
  }

  private partById(id: number): Omit<Part, "current_stock" | "low_stock"> {
    const part = this.state.parts.find((p) => p.id === id && !p.archived);
    if (!part) throw new ApiError(404, "Part not found");
    return part;
  }

  private refreshVehicleMeta(vehicleId: number): void {
    const vehicle = this.state.vehicles.find((v) => v.id === vehicleId);
    if (!vehicle) return;

    const vehicleRecords = this.state.records
      .filter((r) => r.vehicle_id === vehicleId)
      .sort((a, b) => b.performed_at.localeCompare(a.performed_at));
    vehicle.last_service_date = vehicleRecords[0]?.performed_at ?? null;

    const statuses = this.state.reminders
      .filter((r) => r.vehicle_id === vehicleId)
      .map((r) => r.status);
    vehicle.reminder_status = this.worstStatus(statuses);
  }

  private worstStatus(statuses: Reminder["status"][]): Reminder["status"] | null {
    if (statuses.length === 0) return null;
    if (statuses.includes("overdue")) return "overdue";
    if (statuses.includes("due_soon")) return "due_soon";
    return "ok";
  }

  private computeReminderStatus(reminder: Reminder, vehicle: Vehicle): Reminder["status"] {
    const odometer = parseDecimal(vehicle.odometer_km_cached);
    const lastOdo = parseDecimal(reminder.last_service_odometer_km);
    if (reminder.interval_km && odometer - lastOdo >= reminder.interval_km * 0.9) {
      if (odometer - lastOdo >= reminder.interval_km) return "overdue";
      return "due_soon";
    }
    if (reminder.last_service_date && reminder.interval_days) {
      const last = new Date(reminder.last_service_date);
      const now = new Date("2026-07-10");
      const daysSince = Math.floor((now.getTime() - last.getTime()) / 86_400_000);
      if (daysSince >= reminder.interval_days) return "overdue";
      if (daysSince >= reminder.interval_days * 0.9) return "due_soon";
    }
    return "ok";
  }

  private recordWithVehicle(record: MaintenanceRecord): MaintenanceRecordWithVehicle {
    const vehicle = this.state.vehicles.find((v) => v.id === record.vehicle_id);
    return {
      ...record,
      vehicle_plate: vehicle?.plate ?? null,
      vehicle_device_name: vehicle?.device_name ?? null,
    };
  }

  private partsCostForRecord(recordId: number): number {
    const record = this.state.records.find((r) => r.id === recordId);
    if (!record) return 0;
    return record.parts.reduce((sum, line) => {
      const part = this.state.parts.find((p) => p.id === line.part_id);
      const unitCost = part?.unit_cost ? parseDecimal(part.unit_cost) : 0;
      return sum + unitCost * parseDecimal(line.quantity);
    }, 0);
  }

  async login(): Promise<typeof DEMO_USER> {
    await delay();
    return { ...DEMO_USER };
  }

  async logout(): Promise<void> {
    await delay();
  }

  async getMe(): Promise<typeof DEMO_USER> {
    await delay();
    return { ...DEMO_USER };
  }

  async getHealth(): Promise<HealthResponse> {
    await delay();
    return {
      status: "ok",
      database: true,
      traccar_reachable: true,
      traccar_public_url: null,
    };
  }

  async getConfig(): Promise<AppConfigResponse> {
    await delay();
    return { traccar_public_url: null };
  }

  async getVehicles(): Promise<Vehicle[]> {
    await delay();
    const active = this.activeVehicles();
    const registeredDeviceIds = new Set(active.map((v) => v.traccar_device_id));

    const unregistered: Vehicle[] = this.state.unregisteredDevices
      .filter((d) => !registeredDeviceIds.has(d.id))
      .map((d) => ({
        registered: false,
        traccar_device_id: d.id,
        device_name: d.name,
        device_unique_id: d.uniqueId,
        device_status: d.status,
        id: null,
        plate: null,
        vin: null,
        make: null,
        model: null,
        year: null,
        odometer_km_cached: null,
        odometer_synced_at: null,
        engine_hours_cached: null,
        notes: null,
        archived: false,
        last_service_date: null,
        reminder_status: null,
      }));

    return [...active.map(clone), ...unregistered];
  }

  async getVehicle(id: number): Promise<VehicleDetail> {
    await delay();
    const vehicle = clone(this.vehicleById(id));
    const reminders = this.state.reminders
      .filter((r) => r.vehicle_id === id)
      .map(clone);
    const recent_records = this.state.records
      .filter((r) => r.vehicle_id === id)
      .sort((a, b) => b.performed_at.localeCompare(a.performed_at))
      .slice(0, 5)
      .map(clone);
    return { ...vehicle, reminders, recent_records };
  }

  async createVehicle(payload: VehicleCreatePayload): Promise<Vehicle> {
    await delay();
    const device =
      this.state.unregisteredDevices.find((d) => d.id === payload.traccar_device_id) ??
      this.deviceForVehicle(
        this.state.vehicles.find((v) => v.traccar_device_id === payload.traccar_device_id) ?? {
          traccar_device_id: payload.traccar_device_id,
          device_name: `Device ${payload.traccar_device_id}`,
          device_unique_id: `IMEI-${payload.traccar_device_id}`,
          device_status: "online",
        } as Vehicle,
      );

    const id = this.state.nextIds.vehicle++;
    const vehicle: Vehicle = {
      registered: true,
      traccar_device_id: payload.traccar_device_id,
      device_name: device.name,
      device_unique_id: device.uniqueId,
      device_status: device.status,
      id,
      plate: payload.plate ?? null,
      vin: payload.vin ?? null,
      make: payload.make ?? null,
      model: payload.model ?? null,
      year: payload.year ?? null,
      odometer_km_cached: "0",
      odometer_synced_at: new Date().toISOString(),
      engine_hours_cached: null,
      notes: payload.notes ?? null,
      archived: false,
      last_service_date: null,
      reminder_status: null,
    };
    this.state.vehicles.push(vehicle);

    if (payload.create_default_reminders) {
      for (const st of this.state.serviceTypes.slice(0, 3)) {
        this.state.reminders.push({
          id: this.state.nextIds.reminder++,
          vehicle_id: id,
          service_type_id: st.id,
          service_type_name: st.name,
          traccar_maintenance_id: 2000 + id * 10 + st.id,
          traccar_maintenance_type: st.traccar_maintenance_type,
          traccar_maintenance_name: st.name,
          interval_km: st.default_interval_km,
          interval_days: st.default_interval_days,
          interval_hours: null,
          last_service_odometer_km: "0",
          last_service_engine_hours: null,
          last_service_date: null,
          status: "ok",
          sync_error: false,
          created_at: new Date().toISOString(),
        });
      }
      this.refreshVehicleMeta(id);
    }

    return clone(vehicle);
  }

  async bulkCreateVehicles(payload: VehicleBulkCreatePayload): Promise<VehicleBulkCreateResult> {
    await delay();
    const created: Vehicle[] = [];
    const skipped: number[] = [];
    for (const deviceId of payload.traccar_device_ids) {
      const exists = this.state.vehicles.some(
        (v) => v.traccar_device_id === deviceId && !v.archived,
      );
      if (exists) {
        skipped.push(deviceId);
        continue;
      }
      created.push(
        await this.createVehicle({
          traccar_device_id: deviceId,
          create_default_reminders: payload.create_default_reminders,
        }),
      );
    }
    return { created, skipped };
  }

  async updateVehicle(id: number, payload: VehicleUpdatePayload): Promise<Vehicle> {
    await delay();
    const vehicle = this.vehicleById(id);
    Object.assign(vehicle, payload);
    return clone(vehicle);
  }

  async archiveVehicle(id: number): Promise<void> {
    await delay();
    const vehicle = this.vehicleById(id);
    vehicle.archived = true;
  }

  async transferTracker(id: number, payload: VehicleTransferPayload): Promise<VehicleTransferResult> {
    await delay();
    const old = this.vehicleById(id);
    old.archived = true;
    const created = await this.createVehicle({
      traccar_device_id: old.traccar_device_id + 1000,
      plate: payload.plate ?? old.plate ?? undefined,
      vin: payload.vin ?? old.vin ?? undefined,
      make: payload.make ?? old.make ?? undefined,
      model: payload.model ?? old.model ?? undefined,
      year: payload.year ?? old.year ?? undefined,
      notes: payload.notes ?? old.notes ?? undefined,
      create_default_reminders: payload.create_default_reminders,
    });
    if (payload.sync_odometer && old.odometer_km_cached) {
      created.odometer_km_cached = old.odometer_km_cached;
      created.odometer_synced_at = new Date().toISOString();
    }
    return { archived_vehicle_id: id, vehicle: created };
  }

  async syncOdometer(id: number): Promise<Vehicle> {
    await delay();
    const vehicle = this.vehicleById(id);
    const current = parseDecimal(vehicle.odometer_km_cached);
    vehicle.odometer_km_cached = formatDecimal(current + 12.5);
    vehicle.odometer_synced_at = new Date().toISOString();
    for (const reminder of this.state.reminders.filter((r) => r.vehicle_id === id)) {
      reminder.status = this.computeReminderStatus(reminder, vehicle);
    }
    this.refreshVehicleMeta(id);
    return clone(vehicle);
  }

  async syncMaintenance(id: number): Promise<MaintenanceSyncResult> {
    await delay();
    this.vehicleById(id);
    return { synced: 2, created: 0, updated: 1, removed: 0, skipped: 0 };
  }

  async getLogServiceTypes(vehicleId: number): Promise<ServiceType[]> {
    await delay();
    this.vehicleById(vehicleId);
    return this.state.serviceTypes.map(clone);
  }

  async getRecords(vehicleId: number, limit: number, offset: number): Promise<RecordListResponse> {
    await delay();
    const items = this.state.records
      .filter((r) => r.vehicle_id === vehicleId)
      .sort((a, b) => b.performed_at.localeCompare(a.performed_at) || b.id - a.id)
      .map(clone);
    return paginate(items, limit, offset);
  }

  async getAllRecords(limit: number, offset: number): Promise<FleetRecordListResponse> {
    await delay();
    const items = this.state.records
      .sort((a, b) => b.performed_at.localeCompare(a.performed_at) || b.id - a.id)
      .map((r) => this.recordWithVehicle(r));
    return paginate(items, limit, offset);
  }

  async createRecord(vehicleId: number, payload: RecordCreatePayload): Promise<MaintenanceRecord> {
    await delay();
    const vehicle = this.vehicleById(vehicleId);
    const serviceType = this.serviceTypeById(payload.service_type_id);
    const id = this.state.nextIds.record++;
    const parts = (payload.parts ?? []).map((line) => {
      const part = this.partById(line.part_id);
      const qty = String(line.quantity);
      this.state.movements.push({
        id: this.state.nextIds.movement++,
        part_id: line.part_id,
        quantity: `-${qty}`,
        reason: "used_in_service",
        maintenance_record_id: id,
        note: null,
        created_by_traccar_user_id: DEMO_USER.id,
        created_at: new Date().toISOString(),
      });
      return { part_id: part.id, part_name: part.name, quantity: qty };
    });

    const record: MaintenanceRecord = {
      id,
      vehicle_id: vehicleId,
      service_type_id: serviceType.id,
      service_type_name: serviceType.name,
      performed_at: payload.performed_at,
      odometer_km: payload.odometer_km != null ? String(payload.odometer_km) : null,
      cost: payload.cost != null ? String(payload.cost) : null,
      currency: payload.currency ?? "ISK",
      performed_by: payload.performed_by ?? null,
      notes: payload.notes ?? null,
      created_by_traccar_user_id: DEMO_USER.id,
      created_at: new Date().toISOString(),
      parts,
    };
    this.state.records.push(record);

    if (payload.odometer_km != null) {
      vehicle.odometer_km_cached = String(payload.odometer_km);
      vehicle.odometer_synced_at = new Date().toISOString();
    }

    for (const reminder of this.state.reminders.filter(
      (r) => r.vehicle_id === vehicleId && r.service_type_id === serviceType.id,
    )) {
      reminder.last_service_date = payload.performed_at;
      if (payload.odometer_km != null) {
        reminder.last_service_odometer_km = String(payload.odometer_km);
      }
      reminder.status = this.computeReminderStatus(reminder, vehicle);
    }

    this.refreshVehicleMeta(vehicleId);
    return clone(record);
  }

  async updateRecord(recordId: number, payload: RecordUpdatePayload): Promise<MaintenanceRecord> {
    await delay();
    const record = this.state.records.find((r) => r.id === recordId);
    if (!record) throw new ApiError(404, "Record not found");

    if (payload.service_type_id !== undefined) {
      record.service_type_id = payload.service_type_id;
      record.service_type_name = this.serviceTypeById(payload.service_type_id).name;
    }
    if (payload.performed_at !== undefined) record.performed_at = payload.performed_at;
    if (payload.odometer_km !== undefined) {
      record.odometer_km = payload.odometer_km != null ? String(payload.odometer_km) : null;
    }
    if (payload.cost !== undefined) record.cost = payload.cost != null ? String(payload.cost) : null;
    if (payload.currency !== undefined) record.currency = payload.currency;
    if (payload.performed_by !== undefined) record.performed_by = payload.performed_by ?? null;
    if (payload.notes !== undefined) record.notes = payload.notes ?? null;

    this.refreshVehicleMeta(record.vehicle_id);
    return clone(record);
  }

  async getRecord(recordId: number): Promise<MaintenanceRecordDetail> {
    await delay();
    const record = this.state.records.find((r) => r.id === recordId);
    if (!record) throw new ApiError(404, "Record not found");
    const changes: RecordChange[] = [];
    return { ...clone(record), changes };
  }

  async deleteRecord(recordId: number): Promise<void> {
    await delay();
    const index = this.state.records.findIndex((r) => r.id === recordId);
    if (index === -1) throw new ApiError(404, "Record not found");
    const [removed] = this.state.records.splice(index, 1);
    this.state.movements = this.state.movements.filter(
      (m) => m.maintenance_record_id !== recordId,
    );
    this.refreshVehicleMeta(removed.vehicle_id);
  }

  async importRecords(): Promise<ImportResult> {
    await delay();
    return { created: 0, skipped: 0, errors: [] };
  }

  async getServiceTypes(): Promise<ServiceType[]> {
    await delay();
    return this.state.serviceTypes.map(clone);
  }

  async createServiceType(payload: ServiceTypeCreatePayload): Promise<ServiceType> {
    await delay();
    const st: ServiceType = {
      id: this.state.nextIds.serviceType++,
      name: payload.name,
      traccar_maintenance_type: null,
      display_name: payload.name,
      default_interval_km: payload.default_interval_km ?? null,
      default_interval_days: payload.default_interval_days ?? null,
    };
    this.state.serviceTypes.push(st);
    return clone(st);
  }

  async updateServiceType(id: number, payload: ServiceTypeUpdatePayload): Promise<ServiceType> {
    await delay();
    const st = this.serviceTypeById(id);
    if (payload.name !== undefined) {
      st.name = payload.name;
      st.display_name = payload.name;
    }
    if (payload.default_interval_km !== undefined) st.default_interval_km = payload.default_interval_km ?? null;
    if (payload.default_interval_days !== undefined) {
      st.default_interval_days = payload.default_interval_days ?? null;
    }
    return clone(st);
  }

  async deleteServiceType(id: number): Promise<void> {
    await delay();
    const inUse = this.state.records.some((r) => r.service_type_id === id);
    if (inUse) throw new ApiError(409, "Service type is in use");
    this.state.serviceTypes = this.state.serviceTypes.filter((s) => s.id !== id);
  }

  async getServiceTypeRecords(
    serviceTypeId: number,
    limit: number,
    offset: number,
  ): Promise<FleetRecordListResponse> {
    await delay();
    this.serviceTypeById(serviceTypeId);
    const items = this.state.records
      .filter((r) => r.service_type_id === serviceTypeId)
      .sort((a, b) => b.performed_at.localeCompare(a.performed_at))
      .map((r) => this.recordWithVehicle(r));
    return paginate(items, limit, offset);
  }

  async importServiceTypes(): Promise<ImportResult> {
    await delay();
    return { created: 0, skipped: 0, errors: [] };
  }

  async getParts(includeArchived = false): Promise<Part[]> {
    await delay();
    return this.state.parts
      .filter((p) => includeArchived || !p.archived)
      .map((p) => this.enrichPart(p));
  }

  async createPart(payload: PartCreatePayload): Promise<Part> {
    await delay();
    const part: Omit<Part, "current_stock" | "low_stock"> = {
      id: this.state.nextIds.part++,
      sku: payload.sku ?? null,
      name: payload.name,
      unit: payload.unit ?? "pcs",
      min_stock: payload.min_stock != null ? String(payload.min_stock) : "0",
      unit_cost: payload.unit_cost != null ? String(payload.unit_cost) : null,
      archived: false,
      created_at: new Date().toISOString(),
    };
    this.state.parts.push(part);
    return this.enrichPart(part);
  }

  async updatePart(partId: number, payload: PartUpdatePayload): Promise<Part> {
    await delay();
    const part = this.partById(partId);
    if (payload.sku !== undefined) part.sku = payload.sku ?? null;
    if (payload.name !== undefined) part.name = payload.name;
    if (payload.unit !== undefined) part.unit = payload.unit;
    if (payload.min_stock !== undefined) part.min_stock = String(payload.min_stock);
    if (payload.unit_cost !== undefined) {
      part.unit_cost = payload.unit_cost != null ? String(payload.unit_cost) : null;
    }
    if (payload.archived !== undefined) part.archived = payload.archived;
    return this.enrichPart(part);
  }

  async archivePart(partId: number): Promise<void> {
    await delay();
    const part = this.partById(partId);
    part.archived = true;
  }

  async getMovements(partId: number, limit: number, offset: number): Promise<MovementListResponse> {
    await delay();
    this.partById(partId);
    const items = this.state.movements
      .filter((m) => m.part_id === partId)
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .map(clone);
    return paginate(items, limit, offset);
  }

  async createMovement(partId: number, payload: MovementCreatePayload): Promise<StockMovement> {
    await delay();
    this.partById(partId);
    const qty = parseDecimal(payload.quantity);
    const signedQty =
      payload.reason === "purchase" || payload.reason === "return" ? qty : -Math.abs(qty);
    const movement: StockMovement = {
      id: this.state.nextIds.movement++,
      part_id: partId,
      quantity: formatDecimal(signedQty),
      reason: payload.reason,
      maintenance_record_id: null,
      note: payload.note ?? null,
      created_by_traccar_user_id: DEMO_USER.id,
      created_at: new Date().toISOString(),
    };
    this.state.movements.push(movement);
    return clone(movement);
  }

  async getLowStock(): Promise<Part[]> {
    await delay();
    return (await this.getParts()).filter((p) => p.low_stock);
  }

  async importParts(): Promise<ImportResult> {
    await delay();
    return { created: 0, skipped: 0, errors: [] };
  }

  async getReminders(vehicleId: number): Promise<Reminder[]> {
    await delay();
    this.vehicleById(vehicleId);
    return this.state.reminders.filter((r) => r.vehicle_id === vehicleId).map(clone);
  }

  async getAllReminders(): Promise<ReminderWithVehicle[]> {
    await delay();
    return this.state.reminders.map((r) => {
      const vehicle = this.state.vehicles.find((v) => v.id === r.vehicle_id);
      return {
        ...clone(r),
        vehicle_plate: vehicle?.plate ?? null,
        vehicle_device_name: vehicle?.device_name ?? null,
      };
    });
  }

  async createReminder(vehicleId: number, payload: ReminderCreatePayload): Promise<Reminder> {
    await delay();
    const vehicle = this.vehicleById(vehicleId);
    const serviceType = this.serviceTypeById(payload.service_type_id);
    const reminder: Reminder = {
      id: this.state.nextIds.reminder++,
      vehicle_id: vehicleId,
      service_type_id: serviceType.id,
      service_type_name: serviceType.name,
      traccar_maintenance_id: 3000 + vehicleId * 10 + serviceType.id,
      traccar_maintenance_type: serviceType.traccar_maintenance_type,
      traccar_maintenance_name: serviceType.name,
      interval_km: payload.interval_km ?? serviceType.default_interval_km,
      interval_days: payload.interval_days ?? serviceType.default_interval_days,
      interval_hours: payload.interval_hours ?? null,
      last_service_odometer_km:
        payload.last_service_odometer_km != null
          ? String(payload.last_service_odometer_km)
          : null,
      last_service_engine_hours:
        payload.last_service_engine_hours != null
          ? String(payload.last_service_engine_hours)
          : null,
      last_service_date: payload.last_service_date ?? null,
      status: "ok",
      sync_error: false,
      created_at: new Date().toISOString(),
    };
    reminder.status = this.computeReminderStatus(reminder, vehicle);
    this.state.reminders.push(reminder);
    this.refreshVehicleMeta(vehicleId);
    return clone(reminder);
  }

  async updateReminder(reminderId: number, payload: ReminderUpdatePayload): Promise<Reminder> {
    await delay();
    const reminder = this.state.reminders.find((r) => r.id === reminderId);
    if (!reminder) throw new ApiError(404, "Reminder not found");
    const vehicle = this.vehicleById(reminder.vehicle_id);
    if (payload.interval_km !== undefined) reminder.interval_km = payload.interval_km ?? null;
    if (payload.interval_days !== undefined) reminder.interval_days = payload.interval_days ?? null;
    if (payload.interval_hours !== undefined) reminder.interval_hours = payload.interval_hours ?? null;
    if (payload.last_service_odometer_km !== undefined) {
      reminder.last_service_odometer_km =
        payload.last_service_odometer_km != null
          ? String(payload.last_service_odometer_km)
          : null;
    }
    if (payload.last_service_engine_hours !== undefined) {
      reminder.last_service_engine_hours =
        payload.last_service_engine_hours != null
          ? String(payload.last_service_engine_hours)
          : null;
    }
    if (payload.last_service_date !== undefined) {
      reminder.last_service_date = payload.last_service_date ?? null;
    }
    reminder.status = this.computeReminderStatus(reminder, vehicle);
    this.refreshVehicleMeta(reminder.vehicle_id);
    return clone(reminder);
  }

  async deleteReminder(reminderId: number): Promise<void> {
    await delay();
    const index = this.state.reminders.findIndex((r) => r.id === reminderId);
    if (index === -1) throw new ApiError(404, "Reminder not found");
    const [removed] = this.state.reminders.splice(index, 1);
    this.refreshVehicleMeta(removed.vehicle_id);
  }

  async getCostReport(from: string, to: string, vehicleId?: number): Promise<CostReportResponse> {
    await delay();
    const vehicles = this.activeVehicles().filter((v) => vehicleId === undefined || v.id === vehicleId);
    const vehicleIds = new Set(vehicles.map((v) => v.id));

    const filtered = this.state.records.filter(
      (r) =>
        vehicleIds.has(r.vehicle_id) &&
        r.performed_at >= from &&
        r.performed_at <= to,
    );

    const rowMap = new Map<string, CostReportResponse["rows"][number]>();
    let totalLabor = 0;
    let totalParts = 0;
    const currency: string | null = "ISK";

    for (const record of filtered) {
      const vehicle = this.state.vehicles.find((v) => v.id === record.vehicle_id)!;
      const key = `${record.vehicle_id}-${monthKey(record.performed_at)}`;
      const labor = parseDecimal(record.cost);
      const parts = this.partsCostForRecord(record.id);
      totalLabor += labor;
      totalParts += parts;

      const existing = rowMap.get(key);
      if (existing) {
        existing.labor_cost = String(parseDecimal(existing.labor_cost) + labor);
        existing.parts_cost = String(parseDecimal(existing.parts_cost) + parts);
        existing.total_cost = String(parseDecimal(existing.total_cost) + labor + parts);
        existing.record_count += 1;
      } else {
        const [year, month] = monthKey(record.performed_at).split("-").map(Number);
        rowMap.set(key, {
          year,
          month,
          vehicle_id: record.vehicle_id,
          vehicle_plate: vehicle.plate,
          vehicle_device_name: vehicle.device_name,
          currency: record.currency,
          labor_cost: String(labor),
          parts_cost: String(parts),
          total_cost: String(labor + parts),
          record_count: 1,
          km_driven: "1200.0",
          cost_per_km: labor + parts > 0 ? String((labor + parts) / 1200) : null,
          hours_in_period: null,
          cost_per_hour: null,
          odometer_stale: false,
        });
      }
    }

    return {
      from_date: from,
      to_date: to,
      summaries: [
        {
          total_labor_cost: String(totalLabor),
          total_parts_cost: String(totalParts),
          total_cost: String(totalLabor + totalParts),
          record_count: filtered.length,
          currency,
        },
      ],
      rows: [...rowMap.values()].sort(
        (a, b) => b.year - a.year || b.month - a.month || a.vehicle_id - b.vehicle_id,
      ),
    };
  }

  async getCostReportDetail(
    vehicleId: number,
    year: number,
    month: number,
  ): Promise<CostReportDetailResponse> {
    await delay();
    const vehicle = this.vehicleById(vehicleId);
    const prefix = `${year}-${String(month).padStart(2, "0")}`;
    const records = this.state.records.filter(
      (r) => r.vehicle_id === vehicleId && r.performed_at.startsWith(prefix),
    );
    if (records.length === 0) {
      throw new ApiError(404, "No records for this vehicle in the selected month");
    }

    let laborTotal = 0;
    let partsTotal = 0;
    const serviceTypeMap = new Map<number, CostReportDetailResponse["service_type_breakdown"][number]>();
    const partsSummary = new Map<number, CostReportDetailResponse["parts_summary"][number]>();

    const detailRecords = records.map((record) => {
      const labor = parseDecimal(record.cost);
      const partsCost = this.partsCostForRecord(record.id);
      laborTotal += labor;
      partsTotal += partsCost;

      const stRow = serviceTypeMap.get(record.service_type_id) ?? {
        service_type_id: record.service_type_id,
        service_type_name: record.service_type_name ?? "",
        labor_cost: "0",
        parts_cost: "0",
        total_cost: "0",
        record_count: 0,
      };
      stRow.labor_cost = String(parseDecimal(stRow.labor_cost) + labor);
      stRow.parts_cost = String(parseDecimal(stRow.parts_cost) + partsCost);
      stRow.total_cost = String(parseDecimal(stRow.total_cost) + labor + partsCost);
      stRow.record_count += 1;
      serviceTypeMap.set(record.service_type_id, stRow);

      const partLines = record.parts.map((line) => {
        const part = this.state.parts.find((p) => p.id === line.part_id);
        const unitCost = part?.unit_cost ?? null;
        const lineCost = unitCost
          ? parseDecimal(unitCost) * parseDecimal(line.quantity)
          : 0;
        if (part) {
          const agg = partsSummary.get(part.id) ?? {
            part_id: part.id,
            part_name: part.name,
            sku: part.sku,
            unit: part.unit,
            total_quantity: "0",
            total_cost: "0",
          };
          agg.total_quantity = String(
            parseDecimal(agg.total_quantity) + parseDecimal(line.quantity),
          );
          agg.total_cost = String(parseDecimal(agg.total_cost) + lineCost);
          partsSummary.set(part.id, agg);
        }
        return {
          part_id: line.part_id,
          part_name: line.part_name ?? part?.name ?? "",
          sku: part?.sku ?? null,
          unit: part?.unit ?? "pcs",
          quantity: line.quantity,
          unit_cost: unitCost,
          line_cost: String(lineCost),
        };
      });

      return {
        id: record.id,
        service_type_id: record.service_type_id,
        service_type_name: record.service_type_name ?? "",
        performed_at: record.performed_at,
        odometer_km: record.odometer_km,
        labor_cost: record.cost,
        parts_cost: String(partsCost),
        total_cost: String(labor + partsCost),
        currency: record.currency,
        performed_by: record.performed_by,
        notes: record.notes,
        parts: partLines,
      };
    });

    return {
      year,
      month,
      vehicle_id: vehicleId,
      vehicle_plate: vehicle.plate,
      vehicle_device_name: vehicle.device_name,
      currency: records[0].currency,
      labor_cost: String(laborTotal),
      parts_cost: String(partsTotal),
      total_cost: String(laborTotal + partsTotal),
      service_type_breakdown: [...serviceTypeMap.values()],
      records: detailRecords,
      parts_summary: [...partsSummary.values()],
    };
  }

  async getDashboard(): Promise<DashboardResponse> {
    await delay();
    const vehicleIds = new Set(this.activeVehicles().map((v) => v.id));
    const thisMonth = "2026-07";
    const lastMonth = "2026-06";

    let spendThis = 0;
    let spendLast = 0;
    for (const record of this.state.records) {
      if (!vehicleIds.has(record.vehicle_id)) continue;
      const total = parseDecimal(record.cost) + this.partsCostForRecord(record.id);
      if (record.performed_at.startsWith(thisMonth)) spendThis += total;
      if (record.performed_at.startsWith(lastMonth)) spendLast += total;
    }

    const overdue = this.state.reminders.filter(
      (r) => vehicleIds.has(r.vehicle_id) && r.status === "overdue",
    ).length;
    const dueSoon = this.state.reminders.filter(
      (r) => vehicleIds.has(r.vehicle_id) && r.status === "due_soon",
    ).length;
    const lowStock = (await this.getParts()).filter((p) => p.low_stock).length;

    const recent_records = this.state.records
      .filter((r) => vehicleIds.has(r.vehicle_id))
      .sort((a, b) => b.performed_at.localeCompare(a.performed_at))
      .slice(0, 5)
      .map((r) => {
        const vehicle = this.state.vehicles.find((v) => v.id === r.vehicle_id);
        return {
          id: r.id,
          vehicle_id: r.vehicle_id,
          vehicle_plate: vehicle?.plate ?? null,
          vehicle_device_name: vehicle?.device_name ?? null,
          service_type_name: r.service_type_name,
          performed_at: r.performed_at,
          cost: r.cost,
          currency: r.currency,
        };
      });

    return {
      spend_this_month: String(spendThis),
      spend_last_month: String(spendLast),
      currency: "ISK",
      overdue_reminders: overdue,
      due_soon_reminders: dueSoon,
      low_stock_count: lowStock,
      recent_records,
    };
  }

  exportRecordsCsv(from: string, to: string, vehicleId?: number): string {
    const vehicleIds = new Set(
      this.activeVehicles()
        .filter((v) => vehicleId === undefined || v.id === vehicleId)
        .map((v) => v.id),
    );
    const rows = this.state.records.filter(
      (r) =>
        vehicleIds.has(r.vehicle_id) &&
        r.performed_at >= from &&
        r.performed_at <= to,
    );

    const header =
      "date,vehicle_plate,vehicle_device,service_type,odometer_km,labor_cost,parts_cost,total_cost,currency,performed_by,notes\n";
    const body = rows
      .map((record) => {
        const vehicle = this.state.vehicles.find((v) => v.id === record.vehicle_id);
        const labor = parseDecimal(record.cost);
        const parts = this.partsCostForRecord(record.id);
        const fields = [
          record.performed_at,
          vehicle?.plate ?? "",
          vehicle?.device_name ?? "",
          record.service_type_name ?? "",
          record.odometer_km ?? "",
          String(labor),
          String(parts),
          String(labor + parts),
          record.currency,
          record.performed_by ?? "",
          record.notes ?? "",
        ];
        return fields.map((f) => `"${String(f).replace(/"/g, '""')}"`).join(",");
      })
      .join("\n");
    return header + body;
  }
}

export const demoStore = new DemoStore();

export function resetDemoStore(): void {
  demoStore.reset();
}
