import { useState } from "react";

import { useAdminSettings, useAdminUpdateSettings } from "@/hooks/useAdmin";
import { useTranslations } from "@/hooks/useBible";
import { ApiError } from "@/lib/apiError";

function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) return err.message;
  return fallback;
}

export function SettingsTab(): JSX.Element {
  const settingsQuery = useAdminSettings();
  const updateMutation = useAdminUpdateSettings();
  const translationsQuery = useTranslations();
  const [error, setError] = useState<string | null>(null);

  async function handleToggleOpenRegistration(next: boolean): Promise<void> {
    setError(null);
    try {
      await updateMutation.mutateAsync({ open_registration: next });
    } catch (err) {
      setError(errorMessage(err, "Unable to update settings."));
    }
  }

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Registration</h2>

        {settingsQuery.isLoading ? (
          <div
            data-testid="settings-loading"
            className="h-9 w-40 animate-pulse rounded bg-slate-200 dark:bg-slate-800"
          />
        ) : settingsQuery.isError || !settingsQuery.data ? (
          <div
            role="alert"
            className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200"
          >
            Unable to load settings.
          </div>
        ) : (
          <label className="flex items-start gap-3 rounded-md border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900">
            <input
              type="checkbox"
              checked={settingsQuery.data.open_registration}
              disabled={updateMutation.isPending}
              onChange={(e) => {
                void handleToggleOpenRegistration(e.target.checked);
              }}
              className="mt-0.5"
            />
            <div>
              <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
                Open registration
              </div>
              <div className="text-xs text-slate-600 dark:text-slate-300">
                When enabled, anyone who can reach the server can create an account.
                When disabled, only admins can add new users from this page.
              </div>
            </div>
          </label>
        )}

        {error && (
          <p
            role="alert"
            data-testid="settings-error"
            className="text-xs text-rose-700 dark:text-rose-300"
          >
            {error}
          </p>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Translations</h2>
        <p className="text-xs text-slate-600 dark:text-slate-300">
          Translations are loaded from the command line on the server. See the
          docs for{" "}
          <code className="rounded bg-slate-100 px-1 py-0.5 dark:bg-slate-800">
            python -m soap_journal.parsers.&lt;name&gt;
          </code>
          .
        </p>

        {translationsQuery.isLoading ? (
          <div
            data-testid="translations-loading"
            className="h-9 w-40 animate-pulse rounded bg-slate-200 dark:bg-slate-800"
          />
        ) : translationsQuery.isError ? (
          <div
            role="alert"
            className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200"
          >
            Unable to load translations.
          </div>
        ) : (translationsQuery.data?.translations.length ?? 0) === 0 ? (
          <div
            data-testid="translations-empty"
            className="rounded-md border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
          >
            No translations loaded yet. Run the loader CLI to add one.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-md border border-slate-200 dark:border-slate-800">
            <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-800">
              <thead className="bg-slate-50 dark:bg-slate-900">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-slate-600 dark:text-slate-300">
                    Code
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-slate-600 dark:text-slate-300">
                    Name
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-slate-600 dark:text-slate-300">
                    Language
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white dark:divide-slate-800 dark:bg-slate-950">
                {translationsQuery.data?.translations.map((t) => (
                  <tr key={t.code} data-testid={`translation-row-${t.code}`}>
                    <td className="px-3 py-2 font-medium text-slate-900 dark:text-slate-100">
                      {t.code}
                    </td>
                    <td className="px-3 py-2 text-slate-700 dark:text-slate-200">
                      {t.name}
                    </td>
                    <td className="px-3 py-2 text-slate-600 dark:text-slate-300">
                      {t.language}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
