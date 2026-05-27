import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { EntryForm, type EntryFormValues } from "@/components/EntryForm";
import { ApiError } from "@/lib/apiError";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

const baseValues: EntryFormValues = {
  title: "",
  entryDate: "2026-05-27",
  scriptureRef: "John 3:16",
  translationCode: "BSB",
  observation: "obs",
  application: "app",
  prayer: "pray",
  tags: ["faith"],
};

describe("EntryForm", () => {
  it("renders all fields with initialValues", () => {
    renderWithProviders(
      <EntryForm
        initialValues={baseValues}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
        submitLabel="Create entry"
      />,
    );

    expect(screen.getByLabelText(/title/i)).toHaveValue("");
    expect(screen.getByLabelText(/date/i)).toHaveValue("2026-05-27");
    expect(screen.getByLabelText(/scripture reference/i)).toHaveValue("John 3:16");
    expect(screen.getByLabelText(/observation/i)).toHaveValue("obs");
    expect(screen.getByLabelText(/application/i)).toHaveValue("app");
    expect(screen.getByLabelText(/prayer/i)).toHaveValue("pray");
    expect(screen.getByText("faith")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create entry/i })).toBeInTheDocument();
  });

  it("submit calls onSubmit with the current values; empty title passes as empty string", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    renderWithProviders(
      <EntryForm
        initialValues={baseValues}
        onSubmit={onSubmit}
        submitLabel="Create entry"
      />,
    );

    await user.click(screen.getByRole("button", { name: /create entry/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    const args = onSubmit.mock.calls[0]?.[0] as EntryFormValues;
    expect(args.title).toBe("");
    expect(args.scriptureRef).toBe("John 3:16");
    expect(args.tags).toEqual(["faith"]);
  });

  it("INVALID_REFERENCE error shows the message and focuses the scripture ref field", async () => {
    const user = userEvent.setup();
    const onSubmit = vi
      .fn()
      .mockRejectedValue(
        new ApiError(400, "INVALID_REFERENCE", "unknown book: 'Frodo'"),
      );

    renderWithProviders(
      <EntryForm
        initialValues={{ ...baseValues, scriptureRef: "Frodo 3:16" }}
        onSubmit={onSubmit}
        submitLabel="Create entry"
      />,
    );

    await user.click(screen.getByRole("button", { name: /create entry/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/unknown book/i);
    await waitFor(() =>
      expect(document.activeElement).toBe(screen.getByLabelText(/scripture reference/i)),
    );
  });

  it("delete button only renders when onDelete is provided; confirm dialog triggers it", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn().mockResolvedValue(undefined);

    renderWithProviders(
      <EntryForm
        initialValues={baseValues}
        onSubmit={vi.fn()}
        submitLabel="Save changes"
        onDelete={onDelete}
      />,
    );

    await user.click(screen.getByRole("button", { name: /delete entry/i }));
    await user.click(screen.getByRole("button", { name: /^delete$/i }));

    await waitFor(() => expect(onDelete).toHaveBeenCalledTimes(1));
  });

  it("delete button is absent when onDelete is not provided", () => {
    renderWithProviders(
      <EntryForm
        initialValues={baseValues}
        onSubmit={vi.fn()}
        submitLabel="Create entry"
      />,
    );
    expect(screen.queryByRole("button", { name: /delete entry/i })).not.toBeInTheDocument();
  });
});
