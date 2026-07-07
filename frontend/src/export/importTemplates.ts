export const SERVICE_TYPES_IMPORT_HEADERS = [
  "name",
  "default_interval_km",
  "default_interval_days",
];

export const SERVICE_TYPES_IMPORT_EXAMPLE = ["Oil change", "10000", "365"];

export const PARTS_IMPORT_HEADERS = [
  "sku",
  "name",
  "unit",
  "min_stock",
  "unit_cost",
  "initial_stock",
];

export const PARTS_IMPORT_EXAMPLE = ["OF-1", "Oil filter", "pcs", "2", "25.00", "10"];

export const RECORDS_IMPORT_HEADERS = [
  "vehicle_plate",
  "vehicle_device",
  "service_type",
  "performed_at",
  "odometer_km",
  "cost",
  "currency",
  "performed_by",
  "notes",
];

export const RECORDS_IMPORT_EXAMPLE = [
  "AB-123",
  "",
  "Oil change",
  "2026-01-15",
  "95000",
  "15000",
  "ISK",
  "Workshop",
  "",
];
