import { Link } from "react-router-dom";

export function NotFoundPage(): JSX.Element {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <h1 className="text-7xl font-bold">404</h1>
      <p className="mt-3 text-slate-600 dark:text-slate-300">Page not found.</p>
      <Link
        to="/"
        className="mt-6 inline-flex items-center rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
      >
        Back home
      </Link>
    </div>
  );
}
