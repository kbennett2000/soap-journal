import { Link } from "react-router-dom";

/**
 * Catch-all 404 route. Rendered inside Layout so the top bar (theme
 * toggle, log out, admin link) stays available — the user is still on
 * a valid session, just at a URL we don't recognize.
 */
export function NotFoundPage(): JSX.Element {
  return (
    <div className="mx-auto max-w-md space-y-4 rounded-lg border border-slate-200 bg-white p-6 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <h1 className="text-5xl font-bold">404</h1>
      <h2 className="text-lg font-semibold">Page not found</h2>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        We couldn&apos;t find that page. The link may be stale, or the URL was
        mistyped.
      </p>
      <Link
        to="/"
        className="inline-flex h-9 items-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white shadow-sm hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
      >
        Back to dashboard
      </Link>
    </div>
  );
}
