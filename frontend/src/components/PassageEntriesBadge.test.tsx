import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { PassageEntriesBadge } from "@/components/PassageEntriesBadge";
import { server } from "@/test/msw/server";
import {
  makeEntry,
  makePassageEntriesResponse,
} from "@/test/utils/entries";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

describe("PassageEntriesBadge", () => {
  it("renders nothing when count is 0", async () => {
    server.use(
      http.get("/api/v1/bible/passages/entries", () =>
        HttpResponse.json(makePassageEntriesResponse([]), { status: 200 }),
      ),
    );

    const { container } = renderWithProviders(
      <PassageEntriesBadge passageRef="John 3" translationCode="BSB" />,
    );

    // Give the query a chance to resolve.
    await waitFor(() => {
      expect(container.querySelector('[data-testid="passage-entries-badge"]')).toBeNull();
    });
  });

  it("renders the badge with the count when entries exist", async () => {
    server.use(
      http.get("/api/v1/bible/passages/entries", () =>
        HttpResponse.json(
          makePassageEntriesResponse([
            makeEntry({ id: 1, display_title: "First" }),
            makeEntry({ id: 2, display_title: "Second" }),
          ]),
          { status: 200 },
        ),
      ),
    );

    renderWithProviders(
      <PassageEntriesBadge passageRef="John 3" translationCode="BSB" />,
    );

    expect(
      await screen.findByRole("button", { name: /2 entries on this chapter/i }),
    ).toBeInTheDocument();
  });

  it("clicking expands the panel and renders entries; clicking again collapses", async () => {
    server.use(
      http.get("/api/v1/bible/passages/entries", () =>
        HttpResponse.json(
          makePassageEntriesResponse([
            makeEntry({ id: 1, display_title: "Expanded entry" }),
          ]),
          { status: 200 },
        ),
      ),
    );

    const user = userEvent.setup();
    renderWithProviders(
      <PassageEntriesBadge passageRef="John 3" translationCode="BSB" />,
    );

    const trigger = await screen.findByRole("button", {
      name: /1 entry on this chapter/i,
    });
    expect(trigger).toHaveAttribute("aria-expanded", "false");

    await user.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Expanded entry")).toBeInTheDocument();

    await user.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Expanded entry")).not.toBeInTheDocument();
  });
});
