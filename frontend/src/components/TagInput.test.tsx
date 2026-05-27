import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { useState } from "react";

import { TagInput } from "@/components/TagInput";
import { server } from "@/test/msw/server";
import { makeTagSummary } from "@/test/utils/entries";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

function Wrapper({ initial = [] }: { initial?: string[] }): JSX.Element {
  const [value, setValue] = useState<string[]>(initial);
  return <TagInput value={value} onChange={setValue} />;
}

describe("TagInput", () => {
  it("Enter adds a tag", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Wrapper />);
    const input = screen.getByRole("combobox", { name: /tags/i });

    await user.type(input, "faith");
    await user.keyboard("{Enter}");

    expect(screen.getByText("faith")).toBeInTheDocument();
  });

  it("comma adds a tag", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Wrapper />);
    const input = screen.getByRole("combobox", { name: /tags/i });

    await user.type(input, "grace,");

    expect(screen.getByText("grace")).toBeInTheDocument();
    expect(input).toHaveValue("");
  });

  it("Backspace on empty input removes the last tag", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Wrapper initial={["faith", "grace"]} />);
    const input = screen.getByRole("combobox", { name: /tags/i });

    input.focus();
    await user.keyboard("{Backspace}");

    expect(screen.queryByText("grace")).not.toBeInTheDocument();
    expect(screen.getByText("faith")).toBeInTheDocument();
  });

  it("duplicate (case-insensitive) is silently de-duplicated", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Wrapper initial={["Faith"]} />);
    const input = screen.getByRole("combobox", { name: /tags/i });

    await user.type(input, "FAITH");
    await user.keyboard("{Enter}");

    // Still exactly one pill labeled "Faith" (original casing kept).
    expect(screen.getAllByText("Faith")).toHaveLength(1);
  });

  it("whitespace-only Enter is ignored", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Wrapper />);
    const input = screen.getByRole("combobox", { name: /tags/i });

    await user.type(input, "   ");
    await user.keyboard("{Enter}");

    expect(screen.queryAllByRole("button", { name: /^remove tag/i })).toHaveLength(0);
  });

  it("autocomplete suggestions render and clicking one adds it", async () => {
    server.use(
      http.get("/api/v1/tags/autocomplete", () =>
        HttpResponse.json(
          { tags: [makeTagSummary({ id: 1, name: "family", entry_count: 3 })] },
          { status: 200 },
        ),
      ),
    );

    const user = userEvent.setup();
    renderWithProviders(<Wrapper />);
    const input = screen.getByRole("combobox", { name: /tags/i });

    await user.type(input, "fa");
    const option = await screen.findByRole("option", { name: /family/i });
    await user.click(option);

    expect(screen.getByText("family")).toBeInTheDocument();
  });

  it("tag pill × removes the tag", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Wrapper initial={["faith"]} />);

    await user.click(screen.getByRole("button", { name: /remove tag faith/i }));

    expect(screen.queryByText("faith")).not.toBeInTheDocument();
  });

  it("tag exceeding maxTagLength shows hint and is not added", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Wrapper />);
    const input = screen.getByRole("combobox", { name: /tags/i });

    await user.type(input, "x".repeat(51));
    await user.keyboard("{Enter}");

    expect(screen.getByText(/50 characters or fewer/i)).toBeInTheDocument();
    expect(screen.queryAllByRole("button", { name: /^remove tag/i })).toHaveLength(0);
  });
});
