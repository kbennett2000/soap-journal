import { useEffect, useState } from "react";

/**
 * Subscribe to a CSS media query. Used by the reader's panel shell (5c-6) to
 * apply modal semantics + focus-trap only when it's the mobile bottom-sheet
 * (`< lg`), not the desktop docked column. Initial value is read synchronously
 * so the first render is correct; the listener handles later viewport changes.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() =>
    typeof window !== "undefined" && typeof window.matchMedia === "function"
      ? window.matchMedia(query).matches
      : false,
  );

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }
    const mql = window.matchMedia(query);
    const onChange = (): void => setMatches(mql.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}
