import { apiRequest } from "@/lib/api";
import type {
  AdminCreateUserRequest,
  AdminResetPasswordRequest,
  AdminUserListResponse,
  AuthEnvelope,
  SettingsEnvelope,
  SettingsView,
  UserResponse,
} from "@/types/api";

/**
 * Thin wrappers around `apiRequest` for the admin endpoints.
 *
 * Mirrors the unwrapping pattern from `entries.ts`: list/settings
 * responses with meaningful envelope keys pass through as-is, but
 * single-user envelopes are unwrapped at the boundary so callers
 * receive a plain `UserResponse`.
 */

export async function adminListUsers(): Promise<AdminUserListResponse> {
  return apiRequest<AdminUserListResponse>("GET", "/admin/users");
}

export async function adminCreateUser(
  body: AdminCreateUserRequest,
): Promise<UserResponse> {
  const envelope = await apiRequest<AuthEnvelope, AdminCreateUserRequest>(
    "POST",
    "/admin/users",
    { body },
  );
  return envelope.user;
}

export async function adminDeleteUser(userId: number): Promise<void> {
  await apiRequest<void>("DELETE", `/admin/users/${userId}`);
}

export async function adminResetPassword(
  userId: number,
  newPassword: string,
): Promise<void> {
  const body: AdminResetPasswordRequest = { new_password: newPassword };
  await apiRequest<void, AdminResetPasswordRequest>(
    "POST",
    `/admin/users/${userId}/reset-password`,
    { body },
  );
}

export async function adminPromoteUser(userId: number): Promise<UserResponse> {
  const envelope = await apiRequest<AuthEnvelope>(
    "POST",
    `/admin/users/${userId}/promote`,
  );
  return envelope.user;
}

export async function adminDemoteUser(userId: number): Promise<UserResponse> {
  const envelope = await apiRequest<AuthEnvelope>(
    "POST",
    `/admin/users/${userId}/demote`,
  );
  return envelope.user;
}

export async function adminGetSettings(): Promise<SettingsView> {
  const envelope = await apiRequest<SettingsEnvelope>("GET", "/admin/settings");
  return envelope.settings;
}

export async function adminUpdateSettings(
  settings: SettingsView,
): Promise<SettingsView> {
  const envelope = await apiRequest<SettingsEnvelope, SettingsView>(
    "PUT",
    "/admin/settings",
    { body: settings },
  );
  return envelope.settings;
}
