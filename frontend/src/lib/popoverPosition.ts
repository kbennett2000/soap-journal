/**
 * Pure positioning for the selection popover (ADR-0005 5c-6).
 *
 * Given a selection rect, the viewport, and an (estimated) popover size, compute
 * a fixed position that's centered horizontally over the selection and placed
 * ABOVE it — flipping BELOW when there isn't room above — with both axes clamped
 * so the popover stays fully on screen. Kept React-free so it's unit-testable
 * (jsdom can't measure real layout; we assert the math, not pixels).
 */

export interface PositionRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

export interface Viewport {
  width: number;
  height: number;
}

export interface PopoverSize {
  width: number;
  height: number;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(value, max));
}

export function computePopoverPosition(
  rect: PositionRect,
  viewport: Viewport,
  size: PopoverSize,
  pad = 8,
): { top: number; left: number } {
  // Horizontal: centered over the rect, clamped to the viewport. `max(pad, …)`
  // guards a viewport narrower than the popover (pin to the left pad).
  const left = clamp(
    rect.left + rect.width / 2 - size.width / 2,
    pad,
    Math.max(pad, viewport.width - size.width - pad),
  );

  // Vertical: prefer above the selection; flip below when there's no room.
  let top = rect.top - size.height - pad;
  if (top < pad) {
    top = rect.top + rect.height + pad;
  }
  top = clamp(top, pad, Math.max(pad, viewport.height - size.height - pad));

  return { top, left };
}
