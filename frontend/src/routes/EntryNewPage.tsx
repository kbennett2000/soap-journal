import { useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { EntryForm, type EntryFormValues } from "@/components/EntryForm";
import { useCreateEntry } from "@/hooks/useEntries";
import { useTranslations } from "@/hooks/useBible";
import { defaultEntryFormValues } from "@/lib/entryFormDefaults";

interface NewEntryLocationState {
  scriptureRef?: string;
  translationCode?: string;
}

const FALLBACK_TRANSLATION = "BSB";

export function EntryNewPage(): JSX.Element {
  const location = useLocation();
  const navigate = useNavigate();
  const translationsQuery = useTranslations();
  const createMutation = useCreateEntry();

  const state = (location.state as NewEntryLocationState | null) ?? {};

  const defaultTranslation =
    state.translationCode ??
    translationsQuery.data?.translations[0]?.code ??
    FALLBACK_TRANSLATION;

  const initialValues = useMemo<EntryFormValues>(
    () =>
      defaultEntryFormValues({
        translationCode: defaultTranslation,
        scriptureRef: state.scriptureRef,
      }),
    [defaultTranslation, state.scriptureRef],
  );

  async function handleSubmit(values: EntryFormValues): Promise<void> {
    const entry = await createMutation.mutateAsync({
      title: values.title.trim() ? values.title.trim() : null,
      entry_date: values.entryDate,
      scripture_ref: values.scriptureRef,
      translation_code: values.translationCode,
      observation: values.observation,
      application: values.application,
      prayer: values.prayer,
      tags: values.tags,
    });
    navigate(`/entries/${entry.id}`);
  }

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-semibold">New entry</h1>
      <EntryForm
        initialValues={initialValues}
        onSubmit={handleSubmit}
        submitLabel="Create entry"
      />
    </div>
  );
}
