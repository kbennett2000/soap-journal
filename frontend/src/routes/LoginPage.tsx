import { type FormEvent, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { ThemeToggle } from "@/components/ThemeToggle";
import { useAuth } from "@/hooks/useAuth";
import { ApiError } from "@/lib/apiError";

type Mode = "login" | "register";

interface LocationState {
  from?: string;
}

/**
 * Combined login + register form. Two tabs, identical fields.
 *
 * Validation is intentionally light client-side (just the schema-
 * matching min lengths as hints). The backend's `INVALID_REFERENCE`-
 * style structured errors are surfaced via `ApiError.message`.
 */
export function LoginPage(): JSX.Element {
  const { isAuthenticated, isLoading, login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const intended = (location.state as LocationState | null)?.from ?? "/";

  const [mode, setMode] = useState<Mode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Already signed in? Skip the form entirely.
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate(intended, { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate, intended]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setErrorMessage(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(username, password);
      } else {
        await register(username, password);
      }
      navigate(intended, { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const switchMode = (next: Mode): void => {
    setMode(next);
    setErrorMessage(null);
  };

  const usernameHint = "3–32 characters, letters / digits / underscore / hyphen";
  const passwordHint = "at least 8 characters";

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <header className="flex items-center justify-between px-6 py-4">
        <div className="text-lg font-semibold">soap-journal</div>
        <ThemeToggle />
      </header>
      <div className="flex flex-1 items-center justify-center px-4">
        <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-6 flex rounded-md border border-slate-200 p-1 dark:border-slate-700">
            <button
              type="button"
              onClick={() => switchMode("login")}
              className={`flex-1 rounded px-3 py-1.5 text-sm font-medium transition-colors ${
                mode === "login"
                  ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              }`}
            >
              Log in
            </button>
            <button
              type="button"
              onClick={() => switchMode("register")}
              className={`flex-1 rounded px-3 py-1.5 text-sm font-medium transition-colors ${
                mode === "register"
                  ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              }`}
            >
              Register
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="username"
                className="block text-sm font-medium text-slate-700 dark:text-slate-200"
              >
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
                minLength={3}
                maxLength={32}
                className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
              />
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                {usernameHint}
              </p>
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-slate-700 dark:text-slate-200"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                required
                minLength={8}
                className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
              />
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                {passwordHint}
              </p>
            </div>

            {errorMessage && (
              <div
                role="alert"
                className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200"
              >
                {errorMessage}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="inline-flex w-full items-center justify-center rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
            >
              {submitting ? "…" : mode === "login" ? "Log in" : "Register"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
