import type { Strings } from "./i18n";

export function formatKm(value: string | null): string {
  if (value === null) return "—";
  const n = Number(value);
  return `${n.toLocaleString("en-GB", { maximumFractionDigits: 1 })} km`;
}

export function formatCost(value: string | null, currency: string): string {
  if (value === null) return "—";
  return `${Number(value).toLocaleString("en-GB")} ${currency}`;
}

export function formatAgo(iso: string | null, strings: Strings): string | null {
  if (!iso) return null;
  // Backend datetimes are naive UTC.
  const then = new Date(iso.endsWith("Z") ? iso : `${iso}Z`).getTime();
  const minutes = Math.round((Date.now() - then) / 60_000);
  if (minutes < 1) return strings.time.justNow;
  if (minutes < 60) return strings.time.minutesAgo(minutes);
  const hours = Math.round(minutes / 60);
  if (hours < 48) return strings.time.hoursAgo(hours);
  return strings.time.daysAgo(Math.round(hours / 24));
}

export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}
