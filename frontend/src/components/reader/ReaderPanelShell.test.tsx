import { fireEvent, render, screen } from "@testing-library/react";

import { ReaderPanelShell } from "@/components/reader/ReaderPanelShell";

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
});
