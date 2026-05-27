import { Link } from "react-router-dom";

import { useAuth } from "@/hooks/useAuth";

export function DashboardPage(): JSX.Element {
  const { user } = useAuth();
  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-semibold">Welcome, {user?.username ?? "friend"}.</h1>
      <p className="text-slate-600 dark:text-slate-300">
        Dashboard coming soon. For now, the foundation works.
      </p>
      <Link
        to="/read"
        className="inline-flex h-9 items-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white shadow-sm hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
      >
        Open the reader →
      </Link>
    </div>
  );
}
