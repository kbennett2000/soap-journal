/**
 * Tiny shared helpers for rendering Bible text. Kept separate from the
 * components that consume them so the components file only exports
 * components (and Fast Refresh stays happy).
 */

import type { VerseResponse } from "@/types/api";

/**
 * Exact placeholder string the BSB parser substitutes for the 16
 * verses absent from the modern critical text (Matt 17:21, Mark 7:16,
 * John 5:4, ...). Centralized so any layout detecting omitted verses
 * does so the same way.
 */
export const OMITTED_VERSE_PLACEHOLDER = "[Verse omitted in earliest manuscripts.]";

export function isOmittedVerse(verse: VerseResponse): boolean {
  return verse.text === OMITTED_VERSE_PLACEHOLDER;
}
