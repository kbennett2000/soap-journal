import { render } from "@testing-library/react";

import { highlightSnippet } from "@/lib/highlightSnippet";

describe("highlightSnippet", () => {
  it("wraps marked terms in <mark> and keeps surrounding text", () => {
    const { container } = render(
      <div>{highlightSnippet("For God so <mark>loved</mark> the world.")}</div>,
    );
    const mark = container.querySelector("mark");
    expect(mark).not.toBeNull();
    expect(mark?.textContent).toBe("loved");
    expect(container.textContent).toBe("For God so loved the world.");
  });

  it("renders other markup as inert literal text (no injection, no raw <mark>)", () => {
    const { container } = render(
      <div>{highlightSnippet("a <script>alert(1)</script> <mark>b</mark>")}</div>,
    );
    // The <script> from source text is escaped to literal text, not executed.
    expect(container.querySelector("script")).toBeNull();
    expect(container.textContent).toContain("<script>alert(1)</script>");
    // Only the real <mark> element is produced.
    expect(container.querySelectorAll("mark")).toHaveLength(1);
    expect(container.querySelector("mark")?.textContent).toBe("b");
  });

  it("handles multiple marks", () => {
    const { container } = render(
      <div>{highlightSnippet("<mark>a</mark> and <mark>b</mark>")}</div>,
    );
    expect(container.querySelectorAll("mark")).toHaveLength(2);
  });

  it("handles a snippet with no marks", () => {
    const { container } = render(<div>{highlightSnippet("plain text")}</div>);
    expect(container.querySelector("mark")).toBeNull();
    expect(container.textContent).toBe("plain text");
  });
});
