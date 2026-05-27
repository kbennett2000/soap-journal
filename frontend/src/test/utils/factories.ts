import type { UserResponse } from "@/types/api";

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
