import type { ImportReport, UserResponse } from "@/types/api";

/**
 * Build a UserResponse with sensible defaults. Override any field via
 * the partial overrides arg. Kept intentionally tiny — grow as future
 * slices need more shapes.
 */
export function makeUser(overrides: Partial<UserResponse> = {}): UserResponse {
  return {
    id: 1,
    username: "alice",
    is_admin: true,
    created_at: "2026-05-27T00:00:00Z",
    ...overrides,
  };
}

export function makeImportReport(overrides: Partial<ImportReport> = {}): ImportReport {
  return {
    inserted: 0,
    updated: 0,
    skipped_unchanged: 0,
    skipped_missing_translation: 0,
    missing_translations: [],
    total_in_file: 0,
    dry_run: false,
    ...overrides,
  };
}
