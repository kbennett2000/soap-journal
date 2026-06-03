import { apiRequest } from "@/lib/api";
import type { ImportReport } from "@/types/api";

/**
 * Thin wrappers around the per-user backup endpoints.
 *
 * Export is a plain download, so the page links straight to this URL (the
 * session cookie rides along same-origin and the server's Content-Disposition
 * drives the download). Import POSTs the parsed file as a JSON body — the
 * backend reads the raw request body — with `dry_run` in the query string.
 */

export const backupExportUrl = "/api/v1/backup/export";

export function importBackup(document: unknown, dryRun: boolean): Promise<ImportReport> {
  return apiRequest<ImportReport>("POST", "/backup/import", {
    body: document,
    query: { dry_run: dryRun },
  });
}
