import { fireEvent, render, screen, within } from "@testing-library/react";

import { AnnotationPanel } from "@/components/reader/AnnotationPanel";
import { makeAnnotation } from "@/test/utils/bible";

function setup(
  props: Partial<React.ComponentProps<typeof AnnotationPanel>> = {},
) {
  const annotations = props.annotations ?? [makeAnnotation({ id: 1 })];
  const activeId = props.activeId ?? annotations[annotations.length - 1]!.id;
  const handlers = {
    onSelectActive: vi.fn(),
    onChangeColor: vi.fn(),
    onSaveNote: vi.fn(),
    onDelete: vi.fn(),
    onClose: vi.fn(),
  };
  const utils = render(
    <AnnotationPanel
      annotations={annotations}
      activeId={activeId}
      {...handlers}
      {...props}
    />,
  );
  return { ...utils, ...handlers };
}

describe("AnnotationPanel", () => {
  it("renders a single annotation's color, note, and reference (no chooser)", () => {
    setup({
      annotations: [
        makeAnnotation({ id: 1, color: "yellow", note: "my thought" }),
      ],
      activeId: 1,
    });
    expect(screen.getByTestId("annotation-panel")).toBeInTheDocument();
    expect(screen.getByLabelText("Note")).toHaveValue("my thought");
    // ref label (John 3:16 from the builder default) appears in the header.
    expect(screen.getAllByText("John 3:16").length).toBeGreaterThan(0);
    expect(
      screen.queryByRole("group", { name: /overlapping highlights/i }),
    ).not.toBeInTheDocument();
  });

  it("shows a multi-verse reference range", () => {
    setup({
      annotations: [makeAnnotation({ id: 1, verse_start: 16, verse_end: 18 })],
      activeId: 1,
    });
    expect(screen.getAllByText("John 3:16-18").length).toBeGreaterThan(0);
  });

  it("fires onChangeColor with the active id when a different swatch is clicked", () => {
    const { onChangeColor } = setup({
      annotations: [makeAnnotation({ id: 5, color: "yellow" })],
      activeId: 5,
    });
    fireEvent.click(screen.getByLabelText("Set color Green"));
    // Clicking the already-active color is a no-op.
    fireEvent.click(screen.getByLabelText("Set color Yellow"));
    expect(onChangeColor).toHaveBeenCalledTimes(1);
    expect(onChangeColor).toHaveBeenCalledWith(5, "green");
  });

  it("Save is disabled until the note is edited, then fires onSaveNote with the text", () => {
    const { onSaveNote } = setup({
      annotations: [makeAnnotation({ id: 9, note: null })],
      activeId: 9,
    });
    const save = screen.getByRole("button", { name: "Save" });
    expect(save).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Note"), { target: { value: "hello" } });
    expect(save).toBeEnabled();
    fireEvent.click(save);
    expect(onSaveNote).toHaveBeenCalledWith(9, "hello");
  });

  it("trims surrounding whitespace when saving a note", () => {
    const { onSaveNote } = setup({
      annotations: [makeAnnotation({ id: 9, note: null })],
      activeId: 9,
    });
    fireEvent.change(screen.getByLabelText("Note"), {
      target: { value: "  hello  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSaveNote).toHaveBeenCalledWith(9, "hello");
  });

  it("saves an emptied note as null (clear)", () => {
    const { onSaveNote } = setup({
      annotations: [makeAnnotation({ id: 9, note: "existing" })],
      activeId: 9,
    });
    fireEvent.change(screen.getByLabelText("Note"), { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSaveNote).toHaveBeenCalledWith(9, null);
  });

  it("deletes a plain highlight immediately (no confirm)", () => {
    const { onDelete } = setup({
      annotations: [makeAnnotation({ id: 3, note: null })],
      activeId: 3,
    });
    fireEvent.click(screen.getByRole("button", { name: "Delete annotation" }));
    expect(onDelete).toHaveBeenCalledWith(3);
  });

  it("confirms before deleting a highlight that has a note", () => {
    const { onDelete } = setup({
      annotations: [makeAnnotation({ id: 3, note: "keep me?" })],
      activeId: 3,
    });
    fireEvent.click(screen.getByRole("button", { name: "Delete annotation" }));
    expect(onDelete).not.toHaveBeenCalled();
    // The confirm button is named exactly "Delete" (the trigger is "Delete annotation").
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(onDelete).toHaveBeenCalledWith(3);
  });

  it("shows a newest-first stack chooser with the top active; switching active resets the draft", () => {
    const annotations = [
      makeAnnotation({ id: 1, color: "yellow", note: "first" }),
      makeAnnotation({ id: 2, color: "green", note: null }),
      makeAnnotation({ id: 3, color: "blue", note: "third" }),
    ];
    const { onSelectActive, onChangeColor, onSaveNote, onDelete, onClose, rerender } =
      setup({ annotations, activeId: 3 });

    const group = screen.getByRole("group", { name: /overlapping highlights/i });
    const rows = within(group).getAllByTestId("stack-row");
    expect(rows).toHaveLength(3);
    // Newest first → row 0 is id 3 (the active/top one).
    expect(rows[0]).toHaveAttribute("aria-current", "true");
    expect(rows[2]).toHaveAttribute("aria-current", "false");
    // Active = top (id 3) → its note shows.
    expect(screen.getByLabelText("Note")).toHaveValue("third");

    // The last row is the oldest (id 1); clicking it asks the host to switch.
    fireEvent.click(rows[2]!);
    expect(onSelectActive).toHaveBeenCalledWith(1);

    // When the host switches the active id, the draft resets to that note.
    rerender(
      <AnnotationPanel
        annotations={annotations}
        activeId={1}
        onSelectActive={onSelectActive}
        onChangeColor={onChangeColor}
        onSaveNote={onSaveNote}
        onDelete={onDelete}
        onClose={onClose}
      />,
    );
    expect(screen.getByLabelText("Note")).toHaveValue("first");
  });

  it("fires onClose from the close button", () => {
    const { onClose } = setup();
    fireEvent.click(screen.getByRole("button", { name: "Close annotation" }));
    expect(onClose).toHaveBeenCalled();
  });
});
