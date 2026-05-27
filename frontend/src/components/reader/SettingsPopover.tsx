import { useEffect, useRef, useState } from "react";

import type { FontSize, ReaderLayout } from "@/lib/storage";

interface SettingsPopoverProps {
  fontSize: FontSize;
  layout: ReaderLayout;
  onChangeFontSize: (size: FontSize) => void;
  onChangeLayout: (layout: ReaderLayout) => void;
}

const FONT_SIZES: FontSize[] = ["S", "M", "L"];
const LAYOUTS: { value: ReaderLayout; label: string }[] = [
  { value: "verse", label: "Verse" },
  { value: "paragraph", label: "Paragraph" },
];

/**
 * Hand-rolled popover (no UI library). Closes on outside click / Escape.
 */
export function SettingsPopover({
  fontSize,
  layout,
  onChangeFontSize,
  onChangeLayout,
}: SettingsPopoverProps): JSX.Element {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(event: MouseEvent): void {
      if (
        wrapperRef.current &&
        event.target instanceof Node &&
        !wrapperRef.current.contains(event.target)
      ) {
        setOpen(false);
      }
    }
    function handleKey(event: KeyboardEvent): void {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  return (
    <div ref={wrapperRef} className="relative">
      <button
        type="button"
        aria-label="Reader settings"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-300 bg-white text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-5 w-5"
        >
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56V21a2 2 0 0 1-4 0v-.09a1.7 1.7 0 0 0-1.11-1.56 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.56-1.03H3a2 2 0 0 1 0-4h.09a1.7 1.7 0 0 0 1.56-1.11 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.7 1.7 0 0 0 1.87.34h.06a1.7 1.7 0 0 0 1.03-1.56V3a2 2 0 0 1 4 0v.09a1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87v.06a1.7 1.7 0 0 0 1.56 1.03H21a2 2 0 0 1 0 4h-.09a1.7 1.7 0 0 0-1.56 1.03z" />
        </svg>
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Reader settings"
          className="absolute right-0 z-10 mt-2 w-56 rounded-md border border-slate-200 bg-white p-3 shadow-lg dark:border-slate-700 dark:bg-slate-900"
        >
          <div className="mb-3">
            <div className="mb-1 text-xs font-medium text-slate-600 dark:text-slate-300">
              Font size
            </div>
            <div className="flex gap-1">
              {FONT_SIZES.map((size) => (
                <button
                  key={size}
                  type="button"
                  aria-pressed={fontSize === size}
                  onClick={() => onChangeFontSize(size)}
                  className={`h-8 flex-1 rounded text-sm font-medium ${
                    fontSize === size
                      ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                  }`}
                >
                  {size}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="mb-1 text-xs font-medium text-slate-600 dark:text-slate-300">
              Layout
            </div>
            <div className="flex gap-1">
              {LAYOUTS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  aria-pressed={layout === opt.value}
                  onClick={() => onChangeLayout(opt.value)}
                  className={`h-8 flex-1 rounded text-sm font-medium ${
                    layout === opt.value
                      ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
