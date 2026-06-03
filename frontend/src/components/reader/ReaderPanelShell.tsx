import { useEffect, useRef } from "react";

import { useMediaQuery } from "@/hooks/useMediaQuery";

interface ReaderPanelShellProps {
  onClose: () => void;
  children: React.ReactNode;
}

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

function getFocusable(root: HTMLElement | null): HTMLElement[] {
  if (!root) return [];
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
}

/**
 * Responsive host for the reader's side panels (ADR-0005 5c-4/5c-6). ONE element,
 * rendered ONCE: below `lg` it's a slide-up bottom-sheet over a dimmed backdrop;
 * at `lg`+ it's a docked right column. Rendering the content once avoids
 * duplicate testid/`id` collisions.
 *
 * On mobile (the sheet) it gets proper modal semantics (5c-6):
 * `role="dialog"`/`aria-modal`, focus moves into the sheet on open, is trapped
 * while open, and returns to the trigger on close; Escape closes it (deferring
 * to a native `<dialog>` like the delete-confirm). On desktop (docked column)
 * none of that applies — focus flows naturally to/from the page.
 */
export function ReaderPanelShell({
  onClose,
  children,
}: ReaderPanelShellProps): JSX.Element {
  const isSheet = useMediaQuery("(max-width: 1023px)");
  const asideRef = useRef<HTMLElement>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);

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

  // Modal focus management — sheet only. Move focus into the sheet on open and
  // restore it to the trigger on close. Mount-only: the shell remounts whenever
  // the panel reopens, and the viewport class is stable for a device, so the
  // cleanup fires exactly at close (not on a mid-open resize).
  useEffect(() => {
    if (!isSheet) return;
    previouslyFocusedRef.current = document.activeElement as HTMLElement | null;
    asideRef.current?.focus();
    return () => previouslyFocusedRef.current?.focus?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleKeyDown(event: React.KeyboardEvent): void {
    if (!isSheet || event.key !== "Tab") return;
    const focusables = getFocusable(asideRef.current);
    if (focusables.length === 0) {
      event.preventDefault();
      asideRef.current?.focus();
      return;
    }
    const first = focusables[0]!;
    const last = focusables[focusables.length - 1]!;
    const active = document.activeElement;
    if (event.shiftKey) {
      if (active === first || active === asideRef.current) {
        event.preventDefault();
        last.focus();
      }
    } else if (active === last) {
      event.preventDefault();
      first.focus();
    }
  }

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
        ref={asideRef}
        data-testid="reader-panel-shell"
        aria-label="Reader panel"
        role={isSheet ? "dialog" : undefined}
        aria-modal={isSheet ? true : undefined}
        tabIndex={isSheet ? -1 : undefined}
        onKeyDown={handleKeyDown}
        className="fixed inset-x-0 bottom-0 z-40 max-h-[80vh] overflow-y-auto rounded-t-xl bg-white p-4 shadow-2xl outline-none dark:bg-slate-900 lg:sticky lg:top-8 lg:z-auto lg:max-h-[calc(100vh-4rem)] lg:w-96 lg:shrink-0 lg:self-start lg:rounded-none lg:bg-transparent lg:p-0 lg:shadow-none lg:dark:bg-transparent"
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
