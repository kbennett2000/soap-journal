/**
 * Theme persistence helpers.
 *
 * Resolution order (matches the inline `<head>` script in index.html so
 * the class is applied before first paint):
 *   1. `localStorage.theme` if set
 *   2. `prefers-color-scheme` from the OS
 *   3. light
 */

export type Theme = "light" | "dark";

const STORAGE_KEY = "theme";

export function readStoredTheme(): Theme | undefined {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    if (value === "light" || value === "dark") return value;
  } catch {
    // localStorage unavailable (e.g. private mode); fall through.
  }
  return undefined;
}

export function readSystemPreference(): Theme {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return "light";
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function resolveInitialTheme(): Theme {
  return readStoredTheme() ?? readSystemPreference();
}

export function applyThemeClass(theme: Theme): void {
  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
}

export function persistTheme(theme: Theme): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Best-effort; missing localStorage just means non-persistent.
  }
}
