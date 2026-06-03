import { afterEach } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { ReaderPanelShell } from "@/components/reader/ReaderPanelShell";

// The setup mock reports desktop (matches:false). Some tests force the mobile
// sheet by overriding matchMedia; restore it afterward so it can't leak.
const realMatchMedia = window.matchMedia;
afterEach(() => {
  window.matchMedia = realMatchMedia;
});

function mockViewport(isMobile: boolean): void {
  window.matchMedia = ((query: string) =>
    ({
      matches: isMobile,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })) as unknown as typeof window.matchMedia;
}

function setup() {
  const onClose = vi.fn();
  render(
    <ReaderPanelShell onClose={onClose}>
      <div data-testid="content">panel content</div>
    </ReaderPanelShell>,
  );
  return { onClose };
}

describe("ReaderPanelShell", () => {
  it("renders its children exactly once (single content render)", () => {
    setup();
    expect(screen.getAllByTestId("content")).toHaveLength(1);
    expect(screen.getByTestId("reader-panel-shell")).toBeInTheDocument();
    expect(screen.getByTestId("panel-backdrop")).toBeInTheDocument();
  });

  it("closes on Escape", () => {
    const { onClose } = setup();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes on a backdrop tap", () => {
    const { onClose } = setup();
    fireEvent.click(screen.getByTestId("panel-backdrop"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("carries the responsive sheet↔dock class markers (CSS-only switch)", () => {
    // jsdom can't compute layout; assert the responsive classes are present so
    // the bottom-sheet (mobile) → docked-column (lg) switch is wired in CSS.
    setup();
    const shell = screen.getByTestId("reader-panel-shell");
    expect(shell.className).toMatch(/\bfixed\b/); // mobile bottom-sheet
    expect(shell.className).toMatch(/lg:sticky/); // desktop docked column (stays in view)
    expect(shell.className).toMatch(/lg:w-96/);
    expect(screen.getByTestId("panel-backdrop").className).toMatch(/lg:hidden/);
  });

  it("ignores Escape while a native <dialog> is open (the dialog owns it)", () => {
    const onClose = vi.fn();
    render(
      <ReaderPanelShell onClose={onClose}>
        <dialog data-testid="d">
          <button data-testid="b">x</button>
        </dialog>
      </ReaderPanelShell>,
    );
    (screen.getByTestId("d") as HTMLDialogElement).showModal?.();
    screen.getByTestId("b").focus();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).not.toHaveBeenCalled();
  });

  // ---- mobile sheet modal semantics (5c-6) --------------------------------

  it("on mobile, exposes dialog semantics and moves focus into the sheet", () => {
    mockViewport(true);
    render(
      <ReaderPanelShell onClose={vi.fn()}>
        <button data-testid="b">x</button>
      </ReaderPanelShell>,
    );
    const shell = screen.getByTestId("reader-panel-shell");
    expect(shell).toHaveAttribute("role", "dialog");
    expect(shell).toHaveAttribute("aria-modal", "true");
    expect(document.activeElement).toBe(shell); // focus moved in
  });

  it("on mobile, returns focus to the trigger on close", () => {
    mockViewport(true);
    const trigger = document.createElement("button");
    document.body.appendChild(trigger);
    trigger.focus();
    expect(document.activeElement).toBe(trigger);

    const { unmount } = render(
      <ReaderPanelShell onClose={vi.fn()}>
        <button>x</button>
      </ReaderPanelShell>,
    );
    expect(document.activeElement).not.toBe(trigger); // focus moved into sheet

    unmount();
    expect(document.activeElement).toBe(trigger); // restored on close
    trigger.remove();
  });

  it("on desktop (docked), does NOT apply dialog semantics or steal focus", () => {
    mockViewport(false);
    const trigger = document.createElement("button");
    document.body.appendChild(trigger);
    trigger.focus();
    render(
      <ReaderPanelShell onClose={vi.fn()}>
        <button>x</button>
      </ReaderPanelShell>,
    );
    const shell = screen.getByTestId("reader-panel-shell");
    expect(shell).not.toHaveAttribute("role");
    expect(shell).not.toHaveAttribute("aria-modal");
    expect(document.activeElement).toBe(trigger); // focus not stolen
    trigger.remove();
  });
});
