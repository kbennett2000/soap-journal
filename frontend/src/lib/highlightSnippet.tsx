import type { ReactNode } from "react";

/**
 * Render an FTS5 `snippet()` string — plain text with `<mark>…</mark>` around
 * matched terms — as safe React nodes.
 *
 * The snippet is raw verse/note text with literal `<mark>` markers spliced in
 * (FTS5 does not HTML-escape). Rather than `dangerouslySetInnerHTML`, we split
 * on the `<mark>` tokens and emit the surrounding text as React string children
 * (which React escapes) and the matched runs as real `<mark>` elements. Any
 * other markup in the source text therefore renders as inert literal text — no
 * injection, and no raw tags leak through.
 */

const MARK_RE = /<mark>([\s\S]*?)<\/mark>/g;

export function highlightSnippet(snippet: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let markKey = 0;
  MARK_RE.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = MARK_RE.exec(snippet)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(snippet.slice(lastIndex, match.index));
    }
    nodes.push(
      <mark key={`m${markKey++}`} className="rounded bg-amber-200 px-0.5 dark:bg-amber-700/60">
        {match[1]}
      </mark>,
    );
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < snippet.length) {
    nodes.push(snippet.slice(lastIndex));
  }
  return nodes;
}
