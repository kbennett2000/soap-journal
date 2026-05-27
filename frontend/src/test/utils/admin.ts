import type {
  AdminUserListResponse,
  SettingsEnvelope,
  SettingsView,
  UserResponse,
} from "@/types/api";
import { makeUser } from "@/test/utils/factories";

export function makeAdminUserList(
  users: UserResponse[] = [makeUser()],
): AdminUserListResponse {
  return { users };
}

export function makeSettingsView(
  overrides: Partial<SettingsView> = {},
): SettingsView {
  return { open_registration: false, ...overrides };
}

export function makeSettingsEnvelope(
  overrides: Partial<SettingsView> = {},
): SettingsEnvelope {
  return { settings: makeSettingsView(overrides) };
}
