import { computePopoverPosition } from "@/lib/popoverPosition";

const VIEWPORT = { width: 1000, height: 800 };
const SIZE = { width: 240, height: 48 };

describe("computePopoverPosition", () => {
  it("centers horizontally and places above the selection when there's room", () => {
    const pos = computePopoverPosition(
      { top: 300, left: 400, width: 40, height: 16 },
      VIEWPORT,
      SIZE,
    );
    expect(pos.left).toBe(400 + 20 - 120); // 300, centered over the rect
    expect(pos.top).toBe(300 - 48 - 8); // 244, above with padding
  });

  it("clamps the right edge so the popover stays on screen", () => {
    const pos = computePopoverPosition(
      { top: 300, left: 980, width: 40, height: 16 },
      VIEWPORT,
      SIZE,
    );
    expect(pos.left).toBe(1000 - 240 - 8); // 752 (right pad), not off-screen
  });

  it("clamps the left edge", () => {
    const pos = computePopoverPosition(
      { top: 300, left: 0, width: 10, height: 16 },
      VIEWPORT,
      SIZE,
    );
    expect(pos.left).toBe(8); // left pad
  });

  it("flips below the selection when there isn't room above", () => {
    const pos = computePopoverPosition(
      { top: 10, left: 400, width: 40, height: 16 },
      VIEWPORT,
      SIZE,
    );
    expect(pos.top).toBe(10 + 16 + 8); // 34, below the rect
  });

  it("clamps the bottom when there's no room above or below", () => {
    const pos = computePopoverPosition(
      { top: 10, left: 400, width: 40, height: 16 },
      { width: 1000, height: 70 },
      SIZE,
    );
    // below would be 34, but 70 - 48 - 8 = 14 → clamped to 14
    expect(pos.top).toBe(14);
  });

  it("pins to the left pad when the viewport is narrower than the popover", () => {
    const pos = computePopoverPosition(
      { top: 300, left: 100, width: 40, height: 16 },
      { width: 200, height: 800 },
      SIZE,
    );
    expect(pos.left).toBe(8);
  });
});
