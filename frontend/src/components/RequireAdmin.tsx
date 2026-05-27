import { type ReactNode } from "react";

import { useAuth } from "@/hooks/useAuth";

interface RequireAdminProps {
  children: ReactNode;
}

/**
 * Authorization guard for the `/admin` area. Assumes `RequireAuth` runs
 * upstream — by the time we render, the user has a session. If the
 * session doesn't carry `is_admin`, we show a 403 rather than redirect:
 * the user is authenticated, just not authorized, and bouncing them to
 * `/login` would be misleading.
 */
export function RequireAdmin({ children }: RequireAdminProps): JSX.Element {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div
        data-testid="admin-loading"
        className="flex min-h-[50vh] items-center justify-center text-slate-500 dark:text-slate-400"
      >
        Loading…
      </div>
    );
  }

  if (!user?.is_admin) {
    return (
      <div
        role="alert"
        data-testid="admin-forbidden"
        className="mx-auto mt-12 max-w-md rounded-md border border-rose-300 bg-rose-50 px-4 py-6 text-center dark:border-rose-800 dark:bg-rose-950"
      >
        <h1 className="text-lg font-semibold text-rose-800 dark:text-rose-200">
          403 — Forbidden
        </h1>
        <p className="mt-2 text-sm text-rose-700 dark:text-rose-300">
          You don&apos;t have permission to view this page.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
