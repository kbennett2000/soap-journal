import { useCallback, useEffect, useState } from "react";

import {
  applyThemeClass,
  persistTheme,
  resolveInitialTheme,
  type Theme,
} from "@/lib/theme";

export interface UseThemeResult {
  theme: Theme;
  toggle: () => void;
}

export function useTheme(): UseThemeResult {
  // `resolveInitialTheme` reads localStorage + matchMedia; both are
  // available synchronously in the browser, so initial-state lazy init
  // gives us the right value on first render with no hydration flash.
  const [theme, setTheme] = useState<Theme>(() => resolveInitialTheme());

  useEffect(() => {
    applyThemeClass(theme);
    persistTheme(theme);
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  }, []);

  return { theme, toggle };
}
