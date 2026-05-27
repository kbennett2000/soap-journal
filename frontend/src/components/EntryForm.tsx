import { type FormEvent, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EntryFormScripturePreview } from "@/components/EntryFormScripturePreview";
import { TagInput } from "@/components/TagInput";
import { useTranslations } from "@/hooks/useBible";
import { ApiError } from "@/lib/apiError";

export interface EntryFormValues {
  title: string;
  entryDate: string;
  scriptureRef: string;
  translationCode: string;
  observation: string;
  application: string;
  prayer: string;
  tags: string[];
}

interface EntryFormProps {
  initialValues: EntryFormValues;
  onSubmit: (values: EntryFormValues) => Promise<void>;
  submitLabel: string;
  onDelete?: () => Promise<void>;
}

const REF_ERROR_CODES = new Set([
  "INVALID_REFERENCE",
  "CHAPTER_NOT_FOUND",
  "REFERENCE_OUT_OF_RANGE",
  "TRANSLATION_NOT_FOUND",
  "BOOK_NOT_FOUND",
]);

export function EntryForm({
  initialValues,
  onSubmit,
  submitLabel,
  onDelete,
}: EntryFormProps): JSX.Element {
  const navigate = useNavigate();
  const translationsQuery = useTranslations();

  const [title, setTitle] = useState(initialValues.title);
  const [entryDate, setEntryDate] = useState(initialValues.entryDate);
  const [scriptureRef, setScriptureRef] = useState(initialValues.scriptureRef);
  const [translationCode, setTranslationCode] = useState(initialValues.translationCode);
  const [observation, setObservation] = useState(initialValues.observation);
  const [application, setApplication] = useState(initialValues.application);
  const [prayer, setPrayer] = useState(initialValues.prayer);
  const [tags, setTags] = useState<string[]>(initialValues.tags);

  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const refInputRef = useRef<HTMLInputElement>(null);

  // Note: form state is initialized from `initialValues` exactly once
  // (the `useState(() => ...)` calls above). If the parent needs to
  // swap to a different entry's data — e.g. edit page after fetch —
  // it should remount this component by passing a different `key`,
  // not by mutating `initialValues`. That keeps the form's state
  // synchronization to the React lifecycle instead of an effect that
  // would otherwise stomp on user edits.

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setErrorMessage(null);
    setSubmitting(true);
    try {
      await onSubmit({
        title,
        entryDate,
        scriptureRef,
        translationCode,
        observation,
        application,
        prayer,
        tags,
      });
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
        if (REF_ERROR_CODES.has(err.code)) {
          refInputRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
          refInputRef.current?.focus();
        }
      } else {
        setErrorMessage("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  function handleCancel(): void {
    // Try going back; if there's no history, fall back to the list.
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate("/entries");
    }
  }

  async function handleConfirmDelete(): Promise<void> {
    if (!onDelete) return;
    setDeleting(true);
    try {
      await onDelete();
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Unable to delete entry.");
      }
      setConfirmingDelete(false);
    } finally {
      setDeleting(false);
    }
  }

  const translations = translationsQuery.data?.translations ?? [];

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label
          htmlFor="entry-title"
          className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200"
        >
          Title
        </label>
        <input
          id="entry-title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Optional — uses the Scripture reference if blank."
          maxLength={200}
          className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="entry-date"
            className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200"
          >
            Date
          </label>
          <input
            id="entry-date"
            type="date"
            required
            value={entryDate}
            onChange={(e) => setEntryDate(e.target.value)}
            className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          />
        </div>
        <div>
          <label
            htmlFor="entry-translation"
            className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200"
          >
            Translation
          </label>
          <select
            id="entry-translation"
            value={translationCode}
            onChange={(e) => setTranslationCode(e.target.value)}
            className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          >
            {translations.length === 0 && (
              <option value={translationCode}>{translationCode}</option>
            )}
            {translations.map((t) => (
              <option key={t.code} value={t.code}>
                {t.code} — {t.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label
          htmlFor="entry-ref"
          className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200"
        >
          Scripture reference
        </label>
        <input
          id="entry-ref"
          type="text"
          ref={refInputRef}
          required
          value={scriptureRef}
          onChange={(e) => setScriptureRef(e.target.value)}
          placeholder='e.g. "John 3:16" or "Romans 8:28-30"'
          className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        />
        <EntryFormScripturePreview
          scriptureRef={scriptureRef}
          translationCode={translationCode}
        />
      </div>

      <TextareaField
        id="entry-observation"
        label="Observation"
        value={observation}
        onChange={setObservation}
      />
      <TextareaField
        id="entry-application"
        label="Application"
        value={application}
        onChange={setApplication}
      />
      <TextareaField
        id="entry-prayer"
        label="Prayer"
        value={prayer}
        onChange={setPrayer}
      />

      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">
          Tags
        </label>
        <TagInput value={tags} onChange={setTags} />
      </div>

      {errorMessage && (
        <div
          role="alert"
          className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200"
        >
          {errorMessage}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex h-10 items-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white shadow-sm hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
          >
            {submitting ? "Saving…" : submitLabel}
          </button>
          <button
            type="button"
            onClick={handleCancel}
            className="inline-flex h-10 items-center rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            Cancel
          </button>
        </div>
        {onDelete && (
          <button
            type="button"
            onClick={() => setConfirmingDelete(true)}
            disabled={deleting}
            className="inline-flex h-10 items-center rounded-md border border-rose-300 bg-white px-4 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-rose-800 dark:bg-slate-900 dark:text-rose-300 dark:hover:bg-rose-950"
          >
            Delete entry
          </button>
        )}
      </div>

      {onDelete && (
        <ConfirmDialog
          open={confirmingDelete}
          title="Delete entry"
          message="Delete this entry? This cannot be undone."
          confirmLabel={deleting ? "Deleting…" : "Delete"}
          destructive
          onConfirm={() => {
            void handleConfirmDelete();
          }}
          onCancel={() => setConfirmingDelete(false)}
        />
      )}
    </form>
  );
}

interface TextareaFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
}

function TextareaField({ id, label, value, onChange }: TextareaFieldProps): JSX.Element {
  return (
    <div>
      <label
        htmlFor={id}
        className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200"
      >
        {label}
      </label>
      <textarea
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={5}
        className="block w-full resize-y rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
      />
    </div>
  );
}

