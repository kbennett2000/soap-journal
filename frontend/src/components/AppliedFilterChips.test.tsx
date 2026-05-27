import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AppliedFilterChips } from "@/components/AppliedFilterChips";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

describe("AppliedFilterChips", () => {
  it("renders nothing when no filters are applied", () => {
    const { container } = renderWithProviders(
      <AppliedFilterChips
        applied={{ q: null, book: null, tag: null, from_date: null, to_date: null }}
        onRemove={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders one chip per non-null filter", () => {
    renderWithProviders(
      <AppliedFilterChips
        applied={{
          q: "love",
          book: "John",
          tag: "faith",
          from_date: "2026-01-01",
          to_date: "2026-12-31",
        }}
        onRemove={vi.fn()}
      />,
    );

    expect(screen.getByText("love")).toBeInTheDocument();
    expect(screen.getByText("John")).toBeInTheDocument();
    expect(screen.getByText("faith")).toBeInTheDocument();
    expect(screen.getByText("2026-01-01")).toBeInTheDocument();
    expect(screen.getByText("2026-12-31")).toBeInTheDocument();
  });

  it("clicking × on a chip calls onRemove with that filter key", async () => {
    const onRemove = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(
      <AppliedFilterChips
        applied={{
          q: "love",
          book: null,
          tag: "faith",
          from_date: null,
          to_date: null,
        }}
        onRemove={onRemove}
      />,
    );

    await user.click(screen.getByRole("button", { name: /remove tag filter/i }));

    expect(onRemove).toHaveBeenCalledWith("tag");
  });
});
