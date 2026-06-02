import type { HighlightColor } from "@/types/api";

/**
 * The six highlight colors, in palette/swatch order. Mirrors the backend
 * `HighlightColor` Literal and the `--hl-<color>` CSS vars in index.css.
 */
export const HIGHLIGHT_COLORS: readonly HighlightColor[] = [
  "yellow",
  "green",
  "blue",
  "pink",
  "orange",
  "purple",
] as const;

/** Human-readable label for a color swatch's accessible name. */
export const HIGHLIGHT_COLOR_LABELS: Record<HighlightColor, string> = {
  yellow: "Yellow",
  green: "Green",
  blue: "Blue",
  pink: "Pink",
  orange: "Orange",
  purple: "Purple",
};

/**
 * The `background` value for a highlight of the given color — a reference to
 * the theme-aware CSS var so light/dark resolve automatically.
 */
export function highlightVar(color: HighlightColor): string {
  return `var(--hl-${color})`;
}
