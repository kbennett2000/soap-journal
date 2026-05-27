import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";

import {
  adminCreateUser,
  adminDeleteUser,
  adminDemoteUser,
  adminGetSettings,
  adminListUsers,
  adminPromoteUser,
  adminResetPassword,
  adminUpdateSettings,
} from "@/lib/admin";
import type {
  AdminCreateUserRequest,
  AdminUserListResponse,
  SettingsView,
} from "@/types/api";

const USERS_KEY = ["admin", "users"] as const;
const SETTINGS_KEY = ["admin", "settings"] as const;
const ME_KEY = ["auth", "me"] as const;

export function useAdminUsers(): UseQueryResult<AdminUserListResponse> {
  return useQuery({
    queryKey: USERS_KEY,
    queryFn: adminListUsers,
  });
}

export function useAdminSettings(): UseQueryResult<SettingsView> {
  return useQuery({
    queryKey: SETTINGS_KEY,
    queryFn: adminGetSettings,
  });
}

export function useAdminCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AdminCreateUserRequest) => adminCreateUser(body),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: USERS_KEY });
    },
  });
}

export function useAdminDeleteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: number) => adminDeleteUser(userId),
    onSuccess: async () => {
      // If somehow the admin deletes themselves (shouldn't happen — the UI
      // hides the action on your own row — but defense in depth) the cached
      // /me will be stale.
      await Promise.all([
        qc.invalidateQueries({ queryKey: USERS_KEY }),
        qc.invalidateQueries({ queryKey: ME_KEY }),
      ]);
    },
  });
}

export function useAdminResetPassword() {
  return useMutation({
    mutationFn: ({
      userId,
      newPassword,
    }: {
      userId: number;
      newPassword: string;
    }) => adminResetPassword(userId, newPassword),
  });
}

export function useAdminPromoteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: number) => adminPromoteUser(userId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: USERS_KEY });
    },
  });
}

export function useAdminDemoteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: number) => adminDemoteUser(userId),
    onSuccess: async () => {
      // A self-demote will affect /me's is_admin flag; invalidate it too.
      await Promise.all([
        qc.invalidateQueries({ queryKey: USERS_KEY }),
        qc.invalidateQueries({ queryKey: ME_KEY }),
      ]);
    },
  });
}

export function useAdminUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (settings: SettingsView) => adminUpdateSettings(settings),
    onSuccess: (data) => {
      qc.setQueryData(SETTINGS_KEY, data);
    },
  });
}
