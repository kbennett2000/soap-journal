import { useEffect, useId, useRef, useState } from "react";

import { useTagAutocomplete } from "@/hooks/useTags";

interface TagInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  maxTagLength?: number;
}

const DEFAULT_MAX_LEN = 50;
const AUTOCOMPLETE_DEBOUNCE_MS = 150;

/**
 * Chips-style tag entry with autocomplete.
 *
 * Adds a tag on Enter / Tab / comma, removes the last on Backspace from
 * an empty input. Case-insensitive deduplication. Arrow-up/down moves
 * the autocomplete highlight; Enter selects it.
 */
export function TagInput({
  value,
  onChange,
  maxTagLength = DEFAULT_MAX_LEN,
}: TagInputProps): JSX.Element {
  const [input, setInput] = useState("");
  const [debouncedInput, setDebouncedInput] = useState("");
  const [tooLong, setTooLong] = useState(false);
  const [activeIndex, setActiveIndex] = useState<number>(-1);
  const [listboxOpen, setListboxOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const listboxId = useId();

  useEffect(() => {
    const timer = window.setTimeout(
      () => setDebouncedInput(input),
      AUTOCOMPLETE_DEBOUNCE_MS,
    );
    return () => window.clearTimeout(timer);
  }, [input]);

  const autocomplete = useTagAutocomplete(debouncedInput);

  // Filter out tags the user already has; case-insensitive.
  const valueLower = new Set(value.map((t) => t.toLowerCase()));
  const suggestions =
    autocomplete.data?.tags.filter((tag) => !valueLower.has(tag.name.toLowerCase())) ??
    [];

  // Reset active highlight when the suggestion list changes. The
  // setState-in-effect rule discourages this in general, but here the
  // cascade is the desired behavior — a new suggestion set must start
  // unhighlighted regardless of where the previous highlight pointed.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setActiveIndex(-1);
  }, [debouncedInput, autocomplete.data]);

  function tryAddTag(raw: string): boolean {
    const trimmed = raw.trim();
    if (!trimmed) return false;
    if (trimmed.length > maxTagLength) {
      setTooLong(true);
      return false;
    }
    setTooLong(false);
    if (valueLower.has(trimmed.toLowerCase())) {
      // Silent dedup — clearing the input is enough feedback.
      return true;
    }
    onChange([...value, trimmed]);
    return true;
  }

  function removeTagAt(index: number): void {
    onChange(value.filter((_, i) => i !== index));
  }

  function handleInputChange(next: string): void {
    // Comma triggers add: split on the comma and add each piece.
    if (next.includes(",")) {
      const parts = next.split(",");
      const last = parts[parts.length - 1] ?? "";
      for (const part of parts.slice(0, -1)) {
        tryAddTag(part);
      }
      setInput(last);
      return;
    }
    setInput(next);
    if (next.length > maxTagLength) {
      setTooLong(true);
    } else if (tooLong) {
      setTooLong(false);
    }
    setListboxOpen(next.trim().length > 0);
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>): void {
    if (event.key === "Enter" || event.key === "Tab") {
      if (listboxOpen && activeIndex >= 0 && activeIndex < suggestions.length) {
        const picked = suggestions[activeIndex];
        if (picked && tryAddTag(picked.name)) {
          event.preventDefault();
          setInput("");
          setListboxOpen(false);
          return;
        }
      }
      if (input.trim()) {
        event.preventDefault();
        if (tryAddTag(input)) {
          setInput("");
          setListboxOpen(false);
        }
      }
    } else if (event.key === "Backspace" && input === "" && value.length > 0) {
      event.preventDefault();
      removeTagAt(value.length - 1);
    } else if (event.key === "Escape") {
      setListboxOpen(false);
      setActiveIndex(-1);
    } else if (event.key === "ArrowDown" && suggestions.length > 0) {
      event.preventDefault();
      setListboxOpen(true);
      setActiveIndex((prev) => (prev + 1) % suggestions.length);
    } else if (event.key === "ArrowUp" && suggestions.length > 0) {
      event.preventDefault();
      setListboxOpen(true);
      setActiveIndex((prev) =>
        prev <= 0 ? suggestions.length - 1 : prev - 1,
      );
    }
  }

  function handleSuggestionClick(name: string): void {
    if (tryAddTag(name)) {
      setInput("");
      setListboxOpen(false);
      inputRef.current?.focus();
    }
  }

  const showListbox = listboxOpen && suggestions.length > 0;
  const activeId =
    showListbox && activeIndex >= 0 && activeIndex < suggestions.length
      ? `${listboxId}-opt-${suggestions[activeIndex]?.id}`
      : undefined;

  return (
    <div>
      <div className="flex flex-wrap items-center gap-1 rounded-md border border-slate-300 bg-white p-1 focus-within:ring-1 focus-within:ring-slate-500 dark:border-slate-700 dark:bg-slate-800">
        {value.map((tag, i) => (
          <span
            key={`${tag}-${i}`}
            className="inline-flex items-center gap-1 rounded-full bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-700 dark:bg-slate-700 dark:text-slate-200"
          >
            {tag}
            <button
              type="button"
              aria-label={`Remove tag ${tag}`}
              onClick={() => removeTagAt(i)}
              className="rounded text-slate-500 hover:bg-slate-300 hover:text-slate-700 dark:text-slate-300 dark:hover:bg-slate-600 dark:hover:text-slate-100"
            >
              ×
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={showListbox}
          aria-controls={listboxId}
          aria-activedescendant={activeId}
          aria-label="Tags"
          value={input}
          onChange={(e) => handleInputChange(e.target.value)}
          onFocus={() => setListboxOpen(input.trim().length > 0)}
          onKeyDown={handleKeyDown}
          placeholder={value.length === 0 ? "Add a tag…" : ""}
          className="min-w-[6rem] flex-1 bg-transparent px-2 py-1 text-sm text-slate-700 outline-none placeholder:text-slate-400 dark:text-slate-200 dark:placeholder:text-slate-500"
        />
      </div>
      {showListbox && (
        <ul
          id={listboxId}
          role="listbox"
          className="mt-1 max-h-48 overflow-y-auto rounded-md border border-slate-200 bg-white text-sm shadow-lg dark:border-slate-700 dark:bg-slate-900"
        >
          {suggestions.map((tag, i) => (
            <li
              key={tag.id}
              id={`${listboxId}-opt-${tag.id}`}
              role="option"
              aria-selected={i === activeIndex}
              onMouseDown={(e) => {
                // Prevent the input from losing focus before our click.
                e.preventDefault();
              }}
              onClick={() => handleSuggestionClick(tag.name)}
              className={`flex cursor-pointer items-center justify-between px-3 py-1.5 ${
                i === activeIndex
                  ? "bg-slate-100 dark:bg-slate-800"
                  : "hover:bg-slate-50 dark:hover:bg-slate-800"
              }`}
            >
              <span className="text-slate-700 dark:text-slate-200">{tag.name}</span>
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {tag.entry_count}
              </span>
            </li>
          ))}
        </ul>
      )}
      {tooLong && (
        <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">
          Tag must be {maxTagLength} characters or fewer.
        </p>
      )}
    </div>
  );
}
