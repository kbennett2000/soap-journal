import { NavLink, Outlet } from "react-router-dom";

/**
 * Shell for the admin area. Renders a tabbed nav (Users / Settings) and
 * an <Outlet/> for the selected tab; child route is configured in
 * App.tsx. Reachable only via RequireAdmin so we don't repeat the
 * authorization check here.
 */
export function AdminPage(): JSX.Element {
  const base =
    "inline-flex h-9 items-center rounded-md px-3 text-sm font-medium transition-colors";
  const active = "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900";
  const inactive =
    "text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Admin</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
          Manage users and instance settings.
        </p>
      </div>

      <nav
        aria-label="Admin sections"
        className="flex gap-2 border-b border-slate-200 pb-3 dark:border-slate-800"
      >
        <NavLink
          to="/admin/users"
          end
          className={({ isActive }) => `${base} ${isActive ? active : inactive}`}
        >
          Users
        </NavLink>
        <NavLink
          to="/admin/settings"
          end
          className={({ isActive }) => `${base} ${isActive ? active : inactive}`}
        >
          Settings
        </NavLink>
      </nav>

      <Outlet />
    </div>
  );
}
