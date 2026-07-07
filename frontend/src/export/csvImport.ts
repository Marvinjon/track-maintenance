import { downloadTableExport } from "./tableExport";

export function downloadTemplate(
  filename: string,
  headers: string[],
  exampleRow?: string[],
): void {
  downloadTableExport("csv", filename, [
    {
      name: "Template",
      headers,
      rows: exampleRow ? [exampleRow] : [],
    },
  ]);
}

function rowHasData(row: Record<string, string>): boolean {
  return Object.values(row).some((value) => value !== "");
}

/** RFC 4180 CSV parser — no third-party library, safe for user-uploaded files. */
function parseCsvText(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];

    if (inQuotes) {
      if (char === '"' && next === '"') {
        field += '"';
        i += 1;
      } else if (char === '"') {
        inQuotes = false;
      } else {
        field += char;
      }
      continue;
    }

    if (char === '"') {
      inQuotes = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\r" && next === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
      i += 1;
    } else if (char === "\n" || char === "\r") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }

  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }

  return rows;
}

function rowsToObjects(rows: string[][]): Record<string, string>[] {
  if (rows.length === 0) {
    return [];
  }

  const headers = rows[0].map((header) => header.trim());
  const objects: Record<string, string>[] = [];

  for (const values of rows.slice(1)) {
    const row: Record<string, string> = {};
    for (let i = 0; i < headers.length; i += 1) {
      const key = headers[i];
      if (!key) continue;
      row[key] = (values[i] ?? "").trim();
    }
    objects.push(row);
  }

  return objects;
}

export async function parseCsvFile(file: File): Promise<Record<string, string>[]> {
  const text = await file.text();
  const rows = parseCsvText(text);
  if (rows.length === 0) {
    throw new Error("empty");
  }
  return rowsToObjects(rows).filter(rowHasData);
}
