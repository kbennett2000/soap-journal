import { type ReactNode } from "react";
import { Link } from "react-router-dom";

import { ThemeToggle } from "@/components/ThemeToggle";
import { useAuth } from "@/hooks/useAuth";

interface LayoutProps {
  children: ReactNode;
}

/**
 * Authenticated-page chrome: top bar with app name, current username,
 * theme toggle, and logout. Used for every protected page.
 */
export function Layout({ children }: LayoutProps): JSX.Element {
  const { user, logout } = useAuth();

  const handleLogout = async (): Promise<void> => {
    await logout();
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <header className="border-b border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link to="/" className="text-lg font-semibold hover:text-slate-600 dark:hover:text-slate-300">soap-journal</Link>
          <div className="flex items-center gap-3">
            {user?.is_admin && (
              <Link
                to="/admin"
                className="text-sm font-medium text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100"
              >
                Admin
              </Link>
            )}
            {user && (
              <Link
                to="/backup"
                className="text-sm font-medium text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100"
              >
                Backup
              </Link>
            )}
            {user && (
              <span className="text-sm text-slate-600 dark:text-slate-300">
                {user.username}
              </span>
            )}
            <ThemeToggle />
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
    </div>
  );
}
