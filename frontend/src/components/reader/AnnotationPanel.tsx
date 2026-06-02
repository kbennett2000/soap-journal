import { useState } from "react";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import {
  HIGHLIGHT_COLORS,
  HIGHLIGHT_COLOR_LABELS,
  highlightVar,
} from "@/lib/highlightColors";
import type { Annotation, HighlightColor } from "@/types/api";

/**
 * The annotation editor — a PURE content component (no positioning / no
 * backdrop; ReaderPage hosts it, and 5c-4 wraps it in the desktop side-panel /
 * mobile bottom-sheet shell). It edits ONE active annotation: change color
 * (immediate), edit/clear a plain-text note (explicit Save; empty → null),
 * delete (confirm only when a note exists). When a clicked run is covered by
 * more than one highlight, a stack chooser (newest-first) lets the user reach
 * the ones underneath — the active one defaults to the top (newest).
 */

interface AnnotationPanelProps {
  /** The covering stack for the clicked run, id-ascending (top = last). */
  annotations: Annotation[];
  /** Which annotation is being edited (default chosen by the host = top). */
  activeId: number;
  onSelectActive: (id: number) => void;
  onChangeColor: (id: number, color: HighlightColor) => void;
  onSaveNote: (id: number, note: string | null) => void;
  onDelete: (id: number) => void;
  onClose: () => void;
}

function formatRef(a: Annotation): string {
  const base = `${a.book} ${a.chapter}:${a.verse_start}`;
  return a.verse_end > a.verse_start ? `${base}-${a.verse_end}` : base;
}

function hasNote(a: Annotation): boolean {
  return (a.note ?? "").trim().length > 0;
}

export function AnnotationPanel({
  annotations,
  activeId,
  onSelectActive,
  onChangeColor,
  onSaveNote,
  onDelete,
  onClose,
}: AnnotationPanelProps): JSX.Element | null {
  const active = annotations.find((a) => a.id === activeId);

  const [draft, setDraft] = useState(active?.note ?? "");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [trackedId, setTrackedId] = useState(activeId);

  // Reset the editor when the active annotation changes (e.g. switching rows in
  // the stack chooser) — the React-recommended "adjust state during render"
  // pattern, so no effect (and no set-state-in-effect) is needed.
  if (activeId !== trackedId) {
    setTrackedId(activeId);
    setDraft(active?.note ?? "");
    setConfirmOpen(false);
  }

  if (!active) return null;

  const dirty = draft !== (active.note ?? "");

  function handleSave(): void {
    if (!active) return;
    const trimmed = draft.trim();
    onSaveNote(active.id, trimmed === "" ? null : trimmed);
  }

  function requestDelete(): void {
    if (!active) return;
    if (hasNote(active)) {
      setConfirmOpen(true);
    } else {
      onDelete(active.id);
    }
  }

  return (
    <section
      data-testid="annotation-panel"
      aria-label="Annotation"
      className="space-y-3 rounded-md border border-slate-200 bg-white p-3 text-sm dark:border-slate-700 dark:bg-slate-900"
    >
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          <span
            aria-hidden="true"
            className="inline-block h-4 w-4 rounded-full border border-slate-300 dark:border-slate-600"
            style={{ backgroundColor: highlightVar(active.color) }}
          />
          Annotation
          <span className="font-normal normal-case text-slate-400">{formatRef(active)}</span>
        </span>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close annotation"
          className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
        >
          ×
        </button>
      </div>

      {annotations.length > 1 && (
        <div role="group" aria-label="Overlapping highlights" className="space-y-1">
          {[...annotations]
            .sort((x, y) => y.id - x.id) // newest first
            .map((a) => (
              <button
                key={a.id}
                type="button"
                data-testid="stack-row"
                aria-current={a.id === activeId}
                onClick={() => onSelectActive(a.id)}
                className={`flex w-full items-center gap-2 rounded px-2 py-1 text-left ${
                  a.id === activeId
                    ? "bg-slate-100 dark:bg-slate-800"
                    : "hover:bg-slate-50 dark:hover:bg-slate-800/50"
                }`}
              >
                <span
                  aria-hidden="true"
                  className="inline-block h-3 w-3 shrink-0 rounded-full border border-slate-300 dark:border-slate-600"
                  style={{ backgroundColor: highlightVar(a.color) }}
                />
                <span className="flex-1 truncate text-xs text-slate-600 dark:text-slate-300">
                  {formatRef(a)}
                </span>
                {hasNote(a) && (
                  <span
                    role="img"
                    aria-label="has note"
                    title="Has a note"
                    className="text-xs text-slate-400"
                  >
                    ✎
                  </span>
                )}
              </button>
            ))}
        </div>
      )}

      <div className="flex items-center gap-1.5">
        {HIGHLIGHT_COLORS.map((color) => (
          <button
            key={color}
            type="button"
            aria-label={`Set color ${HIGHLIGHT_COLOR_LABELS[color]}`}
            aria-pressed={color === active.color}
            onClick={() => {
              if (color !== active.color) onChangeColor(active.id, color);
            }}
            style={{ backgroundColor: highlightVar(color) }}
            className={`h-6 w-6 rounded-full border transition-transform hover:scale-110 ${
              color === active.color
                ? "border-slate-900 ring-2 ring-slate-900 dark:border-slate-100 dark:ring-slate-100"
                : "border-slate-300 dark:border-slate-600"
            }`}
          />
        ))}
      </div>

      <div className="space-y-1">
        <label
          htmlFor="annotation-note"
          className="block text-xs font-medium text-slate-500 dark:text-slate-400"
        >
          Note
        </label>
        <textarea
          id="annotation-note"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={4}
          placeholder="Add a note…"
          className="w-full rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        />
      </div>

      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={requestDelete}
          aria-label="Delete annotation"
          className="rounded px-2 py-1 text-xs font-medium text-rose-700 hover:bg-rose-50 dark:text-rose-300 dark:hover:bg-rose-900/30"
        >
          Delete
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={!dirty}
          className="rounded-md bg-slate-900 px-3 py-1 text-xs font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
        >
          Save
        </button>
      </div>

      <ConfirmDialog
        open={confirmOpen}
        title="Delete annotation"
        message="This highlight has a note. Delete it anyway?"
        confirmLabel="Delete"
        destructive
        onConfirm={() => {
          setConfirmOpen(false);
          onDelete(active.id);
        }}
        onCancel={() => setConfirmOpen(false)}
      />
    </section>
  );
}
