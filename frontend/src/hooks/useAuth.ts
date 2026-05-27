import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import { apiRequest } from "@/lib/api";
import { ApiError } from "@/lib/apiError";
import type { AuthEnvelope, LoginRequest, RegisterRequest, UserResponse } from "@/types/api";

const ME_KEY = ["auth", "me"] as const;

async function fetchMe(): Promise<UserResponse | undefined> {
  try {
    const envelope = await apiRequest<AuthEnvelope>("GET", "/auth/me");
    return envelope.user;
  } catch (err) {
    // A 401 is the expected "not signed in" state. Anything else (network,
    // server) should still propagate so the user gets a real error.
    if (err instanceof ApiError && err.status === 401) {
      return undefined;
    }
    throw err;
  }
}

export interface UseAuthResult {
  user: UserResponse | undefined;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<UserResponse>;
  register: (username: string, password: string) => Promise<UserResponse>;
  logout: () => Promise<void>;
}

export function useAuth(): UseAuthResult {
  const queryClient = useQueryClient();

  const meQuery = useQuery<UserResponse | undefined>({
    queryKey: ME_KEY,
    queryFn: fetchMe,
    staleTime: 60_000,
  });

  const loginMutation = useMutation({
    mutationFn: async (creds: LoginRequest): Promise<UserResponse> => {
      const envelope = await apiRequest<AuthEnvelope, LoginRequest>(
        "POST",
        "/auth/login",
        { body: creds },
      );
      return envelope.user;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ME_KEY });
      await queryClient.refetchQueries({ queryKey: ME_KEY });
    },
  });

  const registerMutation = useMutation({
    mutationFn: async (creds: RegisterRequest): Promise<UserResponse> => {
      const envelope = await apiRequest<AuthEnvelope, RegisterRequest>(
        "POST",
        "/auth/register",
        { body: creds },
      );
      return envelope.user;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ME_KEY });
      await queryClient.refetchQueries({ queryKey: ME_KEY });
    },
  });

  const logoutMutation = useMutation({
    mutationFn: async (): Promise<void> => {
      await apiRequest<void>("POST", "/auth/logout");
    },
    onSuccess: () => {
      // Drop the cached user. We use `removeQueries` rather than
      // `setQueryData(ME_KEY, undefined)` because react-query v5 treats
      // `undefined` as "no-op" in `setQueryData`, so the prior user
      // would actually stay around. Removing the query forces useQuery
      // to refetch on next render; the server's /auth/me will 401 now
      // that the cookie is gone, and `fetchMe` turns that into undefined.
      queryClient.removeQueries({ queryKey: ME_KEY });
    },
  });

  const login = useCallback(
    async (username: string, password: string): Promise<UserResponse> => {
      return loginMutation.mutateAsync({ username, password });
    },
    [loginMutation],
  );

  const register = useCallback(
    async (username: string, password: string): Promise<UserResponse> => {
      return registerMutation.mutateAsync({ username, password });
    },
    [registerMutation],
  );

  const logout = useCallback(async (): Promise<void> => {
    await logoutMutation.mutateAsync();
  }, [logoutMutation]);

  return {
    user: meQuery.data,
    isLoading: meQuery.isLoading,
    isAuthenticated: meQuery.data !== undefined,
    login,
    register,
    logout,
  };
}
