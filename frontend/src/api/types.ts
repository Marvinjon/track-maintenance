export interface HealthResponse {
  status: string;
  database: boolean;
  traccar_reachable: boolean;
  traccar_public_url: string | null;
}

export interface AppConfigResponse {
  traccar_public_url: string | null;
}

export type ReminderStatus = "ok" | "due_soon" | "overdue";

export interface Vehicle {
  registered: boolean;
  traccar_device_id: number;
  device_name: string | null;
  device_unique_id: string | null;
  device_status: string | null;
  id: number | null;
  plate: string | null;
  vin: string | null;
  make: string | null;
  model: string | null;
  year: number | null;
  odometer_km_cached: string | null;
  odometer_synced_at: string | null;
  engine_hours_cached: string | null;
  notes: string | null;
  archived: boolean;
  last_service_date: string | null;
  reminder_status: ReminderStatus | null;
}

export interface Reminder {
  id: number;
  vehicle_id: number;
  service_type_id: number;
  service_type_name: string | null;
  traccar_maintenance_id: number | null;
  traccar_maintenance_type: string | null;
  traccar_maintenance_name: string | null;
  interval_km: number | null;
  interval_days: number | null;
  interval_hours: number | null;
  last_service_odometer_km: string | null;
  last_service_engine_hours: string | null;
  last_service_date: string | null;
  status: ReminderStatus;
  sync_error: boolean;
  created_at: string;
}

export interface ReminderWithVehicle extends Reminder {
  vehicle_plate: string | null;
  vehicle_device_name: string | null;
}

export interface ReminderCreatePayload {
  service_type_id: number;
  interval_km?: number;
  interval_days?: number;
  interval_hours?: number;
  last_service_odometer_km?: string | number;
  last_service_engine_hours?: string | number;
  last_service_date?: string;
}

export type ReminderUpdatePayload = Omit<ReminderCreatePayload, "service_type_id">;

export interface RecordPart {
  part_id: number;
  part_name: string | null;
  quantity: string;
}

export interface RecordChange {
  id: number;
  field: string;
  old_value: string | null;
  new_value: string | null;
  changed_by_traccar_user_id: number;
  created_at: string;
}

export interface MaintenanceRecord {
  id: number;
  vehicle_id: number;
  service_type_id: number;
  service_type_name: string | null;
  performed_at: string;
  odometer_km: string | null;
  cost: string | null;
  currency: string;
  performed_by: string | null;
  notes: string | null;
  created_by_traccar_user_id: number;
  created_at: string;
  parts: RecordPart[];
}

export interface MaintenanceRecordDetail extends MaintenanceRecord {
  changes: RecordChange[];
}

export interface MaintenanceRecordWithVehicle extends MaintenanceRecord {
  vehicle_plate: string | null;
  vehicle_device_name: string | null;
}

export interface VehicleDetail extends Vehicle {
  reminders: Reminder[];
  recent_records: MaintenanceRecord[];
}

export interface RecordListResponse {
  items: MaintenanceRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface FleetRecordListResponse {
  items: MaintenanceRecordWithVehicle[];
  total: number;
  limit: number;
  offset: number;
}

export interface ServiceType {
  id: number;
  name: string;
  traccar_maintenance_type: string | null;
  display_name: string;
  default_interval_km: number | null;
  default_interval_days: number | null;
}

export interface ServiceTypeCreatePayload {
  name: string;
  default_interval_km?: number;
  default_interval_days?: number;
}

export type ServiceTypeUpdatePayload = Partial<ServiceTypeCreatePayload>;

export interface VehicleCreatePayload {
  traccar_device_id: number;
  plate?: string;
  vin?: string;
  make?: string;
  model?: string;
  year?: number;
  notes?: string;
  create_default_reminders?: boolean;
}

export interface VehicleBulkCreatePayload {
  traccar_device_ids: number[];
  create_default_reminders?: boolean;
}

export interface VehicleBulkCreateResult {
  created: Vehicle[];
  skipped: number[];
}

export interface ServiceTypeCostBreakdown {
  service_type_id: number;
  service_type_name: string;
  labor_cost: string;
  parts_cost: string;
  total_cost: string;
  record_count: number;
}

export interface CostReportPartLine {
  part_id: number;
  part_name: string;
  sku: string | null;
  unit: string;
  quantity: string;
  unit_cost: string | null;
  line_cost: string;
}

export interface CostReportRecordDetail {
  id: number;
  service_type_id: number;
  service_type_name: string;
  performed_at: string;
  odometer_km: string | null;
  labor_cost: string | null;
  parts_cost: string;
  total_cost: string;
  currency: string;
  performed_by: string | null;
  notes: string | null;
  parts: CostReportPartLine[];
}

export interface CostReportPartAggregate {
  part_id: number;
  part_name: string;
  sku: string | null;
  unit: string;
  total_quantity: string;
  total_cost: string;
}

export interface CostReportDetailResponse {
  year: number;
  month: number;
  vehicle_id: number;
  vehicle_plate: string | null;
  vehicle_device_name: string | null;
  currency: string;
  labor_cost: string;
  parts_cost: string;
  total_cost: string;
  service_type_breakdown: ServiceTypeCostBreakdown[];
  records: CostReportRecordDetail[];
  parts_summary: CostReportPartAggregate[];
}

export interface CostReportSummary {
  total_labor_cost: string;
  total_parts_cost: string;
  total_cost: string;
  record_count: number;
  currency: string | null;
}

export interface MonthlyCostRow {
  year: number;
  month: number;
  vehicle_id: number;
  vehicle_plate: string | null;
  vehicle_device_name: string | null;
  currency: string;
  labor_cost: string;
  parts_cost: string;
  total_cost: string;
  record_count: number;
  km_driven: string | null;
  cost_per_km: string | null;
  hours_in_period: string | null;
  cost_per_hour: string | null;
  odometer_stale: boolean;
}

export interface CostReportResponse {
  from_date: string;
  to_date: string;
  summaries: CostReportSummary[];
  rows: MonthlyCostRow[];
}

export interface DashboardRecord {
  id: number;
  vehicle_id: number;
  vehicle_plate: string | null;
  vehicle_device_name: string | null;
  service_type_name: string | null;
  performed_at: string;
  cost: string | null;
  currency: string;
}

export interface DashboardResponse {
  spend_this_month: string;
  spend_last_month: string;
  currency: string | null;
  overdue_reminders: number;
  due_soon_reminders: number;
  low_stock_count: number;
  recent_records: DashboardRecord[];
}

export interface VehicleUpdatePayload {
  plate?: string | null;
  vin?: string;
  make?: string;
  model?: string;
  year?: number;
  notes?: string;
  archived?: boolean;
}

export interface VehicleTransferPayload {
  plate?: string | null;
  vin?: string | null;
  make?: string | null;
  model?: string | null;
  year?: number | null;
  notes?: string | null;
  create_default_reminders?: boolean;
  sync_odometer?: boolean;
}

export interface VehicleTransferResult {
  archived_vehicle_id: number;
  vehicle: Vehicle;
}

export interface MaintenanceSyncResult {
  synced: number;
  created: number;
  updated: number;
  removed: number;
  skipped: number;
}

export interface RecordPartPayload {
  part_id: number;
  quantity: string | number;
}

export interface RecordCreatePayload {
  service_type_id: number;
  performed_at: string;
  odometer_km?: string | number;
  cost?: string | number;
  currency?: string;
  performed_by?: string;
  notes?: string;
  parts?: RecordPartPayload[];
}

export type RecordUpdatePayload = Partial<RecordCreatePayload>;

export interface Part {
  id: number;
  sku: string | null;
  name: string;
  unit: string;
  min_stock: string;
  unit_cost: string | null;
  archived: boolean;
  created_at: string;
  current_stock: string;
  low_stock: boolean;
}

export interface PartCreatePayload {
  sku?: string;
  name: string;
  unit?: string;
  min_stock?: string | number;
  unit_cost?: string | number;
}

export type PartUpdatePayload = Partial<PartCreatePayload> & { archived?: boolean };

export type MovementReason = "purchase" | "used_in_service" | "adjustment" | "return";

export interface StockMovement {
  id: number;
  part_id: number;
  quantity: string;
  reason: MovementReason;
  maintenance_record_id: number | null;
  note: string | null;
  created_by_traccar_user_id: number;
  created_at: string;
}

export interface MovementListResponse {
  items: StockMovement[];
  total: number;
  limit: number;
  offset: number;
}

export interface MovementCreatePayload {
  quantity: string | number;
  reason: Exclude<MovementReason, "used_in_service">;
  note?: string;
}

export interface ImportRowError {
  row: number;
  message: string;
}

export interface ImportResult {
  created: number;
  skipped: number;
  errors: ImportRowError[];
}
