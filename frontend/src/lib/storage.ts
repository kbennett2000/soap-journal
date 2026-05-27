/**
 * Tiny typed wrapper around `localStorage`.
 *
 * All reader persistence — last-read location, font size, layout — funnels
 * through these helpers so the storage keys live in one place and JSON
 * corruption never crashes the page.
 */

export const STORAGE_KEYS = {
  readerLastLocation: "reader.lastLocation",
  readerFontSize: "reader.fontSize",
  readerLayout: "reader.layout",
} as const;

export function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null) return fallback;
    const parsed: unknown = JSON.parse(raw);
    if (parsed === undefined || parsed === null) return fallback;
    return parsed as T;
  } catch {
    // localStorage unavailable, or stored value is non-JSON garbage.
    return fallback;
  }
}

export function writeJson(key: string, value: unknown): void {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Quota exceeded / private mode / etc. — best-effort.
  }
}

export function removeKey(key: string): void {
  try {
    window.localStorage.removeItem(key);
  } catch {
    // Best-effort.
  }
}

// ---- typed reader-specific values -----------------------------------------

export interface ReaderLocation {
  translationCode: string;
  bookName: string;
  chapterNumber: number;
}

export type FontSize = "S" | "M" | "L";
export type ReaderLayout = "verse" | "paragraph";

export function readLastLocation(): ReaderLocation | undefined {
  const value = readJson<ReaderLocation | null>(STORAGE_KEYS.readerLastLocation, null);
  if (!value) return undefined;
  if (
    typeof value.translationCode !== "string" ||
    typeof value.bookName !== "string" ||
    typeof value.chapterNumber !== "number"
  ) {
    return undefined;
  }
  return value;
}

export function writeLastLocation(location: ReaderLocation): void {
  writeJson(STORAGE_KEYS.readerLastLocation, location);
}

export function readFontSize(): FontSize {
  const value = readJson<FontSize | string>(STORAGE_KEYS.readerFontSize, "M");
  return value === "S" || value === "L" ? value : "M";
}

export function writeFontSize(size: FontSize): void {
  writeJson(STORAGE_KEYS.readerFontSize, size);
}

export function readLayout(): ReaderLayout {
  const value = readJson<ReaderLayout | string>(STORAGE_KEYS.readerLayout, "verse");
  return value === "paragraph" ? "paragraph" : "verse";
}

export function writeLayout(layout: ReaderLayout): void {
  writeJson(STORAGE_KEYS.readerLayout, layout);
}
