import * as XLSX from "xlsx";

export type ExportFormat = "csv" | "xlsx";

export type ExportCell = string | number | null | undefined;

export type ExportSheet = {
  name: string;
  headers: string[];
  rows: ExportCell[][];
};

function formatCell(value: ExportCell): string | number {
  if (value === null || value === undefined) return "";
  return value;
}

function escapeCsv(value: ExportCell): string {
  const text = String(formatCell(value));
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function sanitizeSheetName(name: string): string {
  const cleaned = name.replace(/[:\\/?*[\]]/g, "").trim();
  return (cleaned || "Sheet").slice(0, 31);
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function sheetToCsv(sheet: ExportSheet): string[] {
  const lines = [sheet.headers.map(escapeCsv).join(",")];
  for (const row of sheet.rows) {
    lines.push(row.map(escapeCsv).join(","));
  }
  return lines;
}

export function downloadTableExport(
  format: ExportFormat,
  filename: string,
  sheets: ExportSheet[],
) {
  const base = filename.replace(/\.(csv|xlsx)$/i, "");

  if (format === "csv") {
    const lines: string[] = [];
    for (const [index, sheet] of sheets.entries()) {
      if (sheets.length > 1) {
        if (index > 0) lines.push("");
        lines.push(sheet.name);
      }
      lines.push(...sheetToCsv(sheet));
    }
    const blob = new Blob([`\uFEFF${lines.join("\n")}`], {
      type: "text/csv;charset=utf-8",
    });
    downloadBlob(blob, `${base}.csv`);
    return;
  }

  const workbook = XLSX.utils.book_new();
  const usedNames = new Set<string>();
  for (const sheet of sheets) {
    let name = sanitizeSheetName(sheet.name);
    let suffix = 2;
    while (usedNames.has(name)) {
      const stem = sanitizeSheetName(sheet.name).slice(0, 28);
      name = `${stem}_${suffix}`;
      suffix += 1;
    }
    usedNames.add(name);
    const data = [sheet.headers, ...sheet.rows.map((row) => row.map(formatCell))];
    const worksheet = XLSX.utils.aoa_to_sheet(data);
    XLSX.utils.book_append_sheet(workbook, worksheet, name);
  }
  XLSX.writeFile(workbook, `${base}.xlsx`);
}
