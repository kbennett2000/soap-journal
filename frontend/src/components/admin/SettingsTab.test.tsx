import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { SettingsTab } from "@/components/admin/SettingsTab";
import { server } from "@/test/msw/server";
import { makeSettingsEnvelope } from "@/test/utils/admin";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

describe("SettingsTab", () => {
  it("reflects the loaded open_registration value", async () => {
    server.use(
      http.get("/api/v1/admin/settings", () =>
        HttpResponse.json(makeSettingsEnvelope({ open_registration: true }), {
          status: 200,
        }),
      ),
    );

    renderWithProviders(<SettingsTab />);

    const checkbox = await screen.findByRole("checkbox", {
      name: /open registration/i,
    });
    expect(checkbox).toBeChecked();
  });

  it("PUTs the toggled value when the user clicks the checkbox", async () => {
    let receivedBody: { open_registration: boolean } | null = null;
    server.use(
      http.get("/api/v1/admin/settings", () =>
        HttpResponse.json(makeSettingsEnvelope({ open_registration: false }), {
          status: 200,
        }),
      ),
      http.put("/api/v1/admin/settings", async ({ request }) => {
        receivedBody = (await request.json()) as typeof receivedBody;
        return HttpResponse.json(
          makeSettingsEnvelope({ open_registration: true }),
          { status: 200 },
        );
      }),
    );

    const user = userEvent.setup();
    renderWithProviders(<SettingsTab />);

    const checkbox = await screen.findByRole("checkbox", {
      name: /open registration/i,
    });
    expect(checkbox).not.toBeChecked();

    await user.click(checkbox);

    await waitFor(() =>
      expect(receivedBody).toEqual({ open_registration: true }),
    );
    await waitFor(() => expect(checkbox).toBeChecked());
  });

  it("shows the no-translations hint when none are loaded", async () => {
    server.use(
      http.get("/api/v1/bible/translations", () =>
        HttpResponse.json({ translations: [] }, { status: 200 }),
      ),
    );

    renderWithProviders(<SettingsTab />);

    expect(
      await screen.findByTestId("translations-empty"),
    ).toBeInTheDocument();
  });

  it("renders an error banner if updating settings fails", async () => {
    server.use(
      http.get("/api/v1/admin/settings", () =>
        HttpResponse.json(makeSettingsEnvelope({ open_registration: false }), {
          status: 200,
        }),
      ),
      http.put("/api/v1/admin/settings", () =>
        HttpResponse.json(
          { detail: { code: "BOOM", message: "couldn't save settings" } },
          { status: 500 },
        ),
      ),
    );

    const user = userEvent.setup();
    renderWithProviders(<SettingsTab />);

    const checkbox = await screen.findByRole("checkbox", {
      name: /open registration/i,
    });
    await user.click(checkbox);

    await waitFor(() =>
      expect(screen.getByTestId("settings-error")).toHaveTextContent(
        /couldn't save settings/i,
      ),
    );
  });
});
