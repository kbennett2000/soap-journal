import { useEffect } from "react";

interface ReaderPanelShellProps {
  onClose: () => void;
  children: React.ReactNode;
}

/**
 * Responsive host for the reader's side panels (ADR-0005 5c-4). ONE element,
 * rendered ONCE: below `lg` it's a slide-up bottom-sheet over a dimmed backdrop;
 * at `lg`+ it's a docked right column (the parent single-pane region is a
 * `lg:flex` row, reader `flex-1`, this the second child). Rendering the content
 * once — rather than a desktop + mobile copy — avoids duplicate testid/`id`
 * collisions. Escape, the Close control inside the content, and (mobile) a
 * backdrop tap all dismiss. Drag-to-resize is intentionally out of scope (5c-4).
 */
export function ReaderPanelShell({
  onClose,
  children,
}: ReaderPanelShellProps): JSX.Element {
  useEffect(() => {
    function onKey(event: KeyboardEvent): void {
      if (event.key !== "Escape") return;
      // A native <dialog> (e.g. the delete-confirm) traps focus and owns Escape;
      // don't let the shell also close underneath it when the user cancels it.
      const active = document.activeElement;
      if (active?.closest("dialog")) return;
      onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      {/* Mobile-only dimmed backdrop; the desktop dock has none. */}
      <div
        data-testid="panel-backdrop"
        aria-hidden="true"
        onClick={onClose}
        className="fixed inset-0 z-30 bg-black/40 lg:hidden"
      />
      <aside
        data-testid="reader-panel-shell"
        aria-label="Reader panel"
        className="fixed inset-x-0 bottom-0 z-40 max-h-[80vh] overflow-y-auto rounded-t-xl bg-white p-4 shadow-2xl dark:bg-slate-900 lg:sticky lg:top-8 lg:z-auto lg:max-h-[calc(100vh-4rem)] lg:w-96 lg:shrink-0 lg:self-start lg:rounded-none lg:bg-transparent lg:p-0 lg:shadow-none lg:dark:bg-transparent"
      >
        {/* Drag-handle affordance (visual only; mobile). */}
        <div
          aria-hidden="true"
          className="mx-auto mb-3 h-1 w-10 rounded-full bg-slate-300 dark:bg-slate-600 lg:hidden"
        />
        {children}
      </aside>
    </>
  );
}
