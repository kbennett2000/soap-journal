import {
  HIGHLIGHT_COLORS,
  HIGHLIGHT_COLOR_LABELS,
  highlightVar,
} from "@/lib/highlightColors";

describe("highlightColors", () => {
  it("exposes the six palette colors", () => {
    expect(HIGHLIGHT_COLORS).toEqual([
      "yellow",
      "green",
      "blue",
      "pink",
      "orange",
      "purple",
    ]);
  });

  it("maps each color to its theme-aware CSS var", () => {
    expect(highlightVar("yellow")).toBe("var(--hl-yellow)");
    expect(highlightVar("purple")).toBe("var(--hl-purple)");
  });

  it("has a label for every color", () => {
    for (const color of HIGHLIGHT_COLORS) {
      expect(HIGHLIGHT_COLOR_LABELS[color]).toBeTruthy();
    }
  });
});
