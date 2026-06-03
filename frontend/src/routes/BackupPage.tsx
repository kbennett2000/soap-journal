import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import { invalidateAllEntryViews } from "@/hooks/useEntries";
import { ApiError } from "@/lib/apiError";
import { backupExportUrl, importBackup } from "@/lib/backup";

const primaryButton =
  "inline-flex h-9 items-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white shadow-sm hover:bg-slate-800 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200";
const secondaryButton =
  "inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700";
const cardClass =
  "space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900";

/** Turn any thrown error into a calm, user-facing message. */
function importErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === "BACKUP_VERSION_UNSUPPORTED") {
      return "This backup is from a newer version of the app.";
    }
    if (err.code === "NETWORK_ERROR") {
      return "Couldn't reach the server.";
    }
    // INVALID_BACKUP and anything else carry a server-friendly message.
    return err.message;
  }
  return "Something went wrong importing the file.";
}

export function BackupPage(): JSX.Element {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [parsed, setParsed] = useState<unknown | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  const preview = useMutation({
    mutationFn: (document: unknown) => importBackup(document, true),
  });
  const confirm = useMutation({
    mutationFn: (document: unknown) => importBackup(document, false),
    onSuccess: () => invalidateAllEntryViews(queryClient),
  });

  function resetImport(): void {
    setParsed(null);
    setFileError(null);
    preview.reset();
    confirm.reset();
  }

  async function handleFileChange(
    event: React.ChangeEvent<HTMLInputElement>,
  ): Promise<void> {
    resetImport();
    const file = event.target.files?.[0];
    if (!file) return;

    let document: unknown;
    try {
      document = JSON.parse(await file.text());
    } catch {
      setFileError("This file isn't valid JSON.");
      return;
    }
    setParsed(document);
    preview.mutate(document);
  }

  function handleConfirm(): void {
    if (parsed !== null) confirm.mutate(parsed);
  }

  function handleCancel(): void {
    resetImport();
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">Backup &amp; Restore</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          {user ? `Signed in as ${user.username}. ` : ""}
          Export downloads your journal as a file you can move to your phone or
          keep as a backup. Import <strong>merges</strong> a file into your
          journal — it adds new entries and updates ones you edited more recently
          (last-write-wins), and never deletes anything.
        </p>
      </header>

      <section className={cardClass} aria-labelledby="export-heading">
        <h2 id="export-heading" className="text-lg font-medium">
          Export
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Download a copy of every entry in your journal.
        </p>
        <a href={backupExportUrl} className={primaryButton}>
          Export backup
        </a>
      </section>

      <section className={cardClass} aria-labelledby="import-heading">
        <h2 id="import-heading" className="text-lg font-medium">
          Import
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Choose a backup file to preview what would change before importing.
        </p>

        <div className="space-y-1">
          <label
            htmlFor="backup-file"
            className="block text-sm font-medium text-slate-700 dark:text-slate-200"
          >
            Backup file
          </label>
          <input
            id="backup-file"
            ref={fileInputRef}
            type="file"
            accept=".json,application/json"
            onChange={handleFileChange}
            className="block text-sm text-slate-600 file:mr-3 file:rounded-md file:border file:border-slate-300 file:bg-white file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-slate-100 dark:text-slate-300 dark:file:border-slate-700 dark:file:bg-slate-800"
          />
        </div>

        {fileError && (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400">
            {fileError}
          </p>
        )}

        {preview.isPending && (
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Checking the file…
          </p>
        )}
        {preview.isError && (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400">
            {importErrorMessage(preview.error)}
          </p>
        )}

        {confirm.isSuccess ? (
          <div
            className="space-y-1 rounded-md border border-green-200 bg-green-50 p-4 text-sm text-green-800 dark:border-green-900 dark:bg-green-950 dark:text-green-200"
            role="status"
          >
            <p className="font-medium">
              Imported {confirm.data.inserted} new, {confirm.data.updated}{" "}
              updated, {confirm.data.skipped_unchanged} unchanged.
            </p>
            {confirm.data.missing_translations.length > 0 && (
              <p>
                Skipped {confirm.data.skipped_missing_translation} entries in
                translations not loaded on this server:{" "}
                {confirm.data.missing_translations.join(", ")}.
              </p>
            )}
          </div>
        ) : preview.isSuccess ? (
          <div className="space-y-3 rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800">
            <p className="text-sm text-slate-700 dark:text-slate-200">
              Would import: {preview.data.inserted} new, {preview.data.updated}{" "}
              updated, {preview.data.skipped_unchanged} unchanged.
            </p>
            {preview.data.missing_translations.length > 0 && (
              <p className="text-sm text-amber-700 dark:text-amber-300">
                Skipped {preview.data.skipped_missing_translation} entries that
                use translations not loaded on this server:{" "}
                {preview.data.missing_translations.join(", ")}. Once those are
                added, re-import to include them.
              </p>
            )}
            {confirm.isError && (
              <p role="alert" className="text-sm text-red-600 dark:text-red-400">
                {importErrorMessage(confirm.error)}
              </p>
            )}
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleConfirm}
                disabled={confirm.isPending}
                className={primaryButton}
              >
                {confirm.isPending ? "Importing…" : "Confirm import"}
              </button>
              <button
                type="button"
                onClick={handleCancel}
                disabled={confirm.isPending}
                className={secondaryButton}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
