import type { EntryFormValues } from "@/components/EntryForm";

/**
 * Default `EntryFormValues` for a brand-new entry. Lives in `lib/` so
 * components that export only React components (per the react-refresh
 * rule) don't have to share their files with helper utilities.
 */
export function defaultEntryFormValues(opts: {
  translationCode: string;
  scriptureRef?: string;
}): EntryFormValues {
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, "0");
  const dd = String(today.getDate()).padStart(2, "0");
  return {
    title: "",
    entryDate: `${yyyy}-${mm}-${dd}`,
    scriptureRef: opts.scriptureRef ?? "",
    translationCode: opts.translationCode,
    observation: "",
    application: "",
    prayer: "",
    tags: [],
  };
}
