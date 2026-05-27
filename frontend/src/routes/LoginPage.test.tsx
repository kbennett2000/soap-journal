import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router-dom";

import { LoginPage } from "@/routes/LoginPage";
import { server } from "@/test/msw/server";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

/**
 * Mount LoginPage at /login with a tiny `/` route that renders a
 * recognizable marker. Tests assert the marker shows up after a
 * successful auth as a proxy for "router navigated to /".
 */
function renderLogin(initialEntries: string[] = ["/login"]) {
  return renderWithProviders(
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<div>HOME</div>} />
    </Routes>,
    { initialEntries },
  );
}

async function ensureLoggedOut() {
  server.use(
    http.get("/api/v1/auth/me", () =>
      HttpResponse.json(
        { detail: { code: "NOT_AUTHENTICATED", message: "NOT_AUTHENTICATED" } },
        { status: 401 },
      ),
    ),
  );
}

// LoginPage uses the same label on the tab button and the submit
// button ("Log in" / "Register"). Disambiguate by HTMLButtonElement.type
// — tabs are type="button", the form submit is type="submit".
function getTab(name: RegExp): HTMLButtonElement {
  const button = screen
    .getAllByRole("button", { name })
    .find((b) => (b as HTMLButtonElement).type === "button");
  if (!button) throw new Error(`No tab button matching ${name}`);
  return button as HTMLButtonElement;
}

function getSubmit(name: RegExp): HTMLButtonElement {
  const button = screen
    .getAllByRole("button", { name })
    .find((b) => (b as HTMLButtonElement).type === "submit");
  if (!button) throw new Error(`No submit button matching ${name}`);
  return button as HTMLButtonElement;
}

describe("LoginPage", () => {
  it("renders both Log in and Register tabs", async () => {
    await ensureLoggedOut();
    renderLogin();
    await screen.findByLabelText(/username/i);

    expect(getTab(/^log in$/i)).toBeInTheDocument();
    expect(getTab(/^register$/i)).toBeInTheDocument();
  });

  it("logs in with valid credentials and lands on /", async () => {
    await ensureLoggedOut();
    const user = userEvent.setup();
    renderLogin();
    await screen.findByLabelText(/username/i);

    await user.type(screen.getByLabelText(/username/i), "alice");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(getSubmit(/^log in$/i));

    await waitFor(() => expect(screen.getByText("HOME")).toBeInTheDocument());
  });

  it("shows the server's INVALID_CREDENTIALS message when login fails", async () => {
    await ensureLoggedOut();
    server.use(
      http.post("/api/v1/auth/login", () =>
        HttpResponse.json(
          { detail: { code: "INVALID_CREDENTIALS", message: "INVALID_CREDENTIALS" } },
          { status: 401 },
        ),
      ),
    );

    const user = userEvent.setup();
    renderLogin();
    await screen.findByLabelText(/username/i);

    await user.type(screen.getByLabelText(/username/i), "alice");
    await user.type(screen.getByLabelText(/password/i), "wrongpassword");
    await user.click(getSubmit(/^log in$/i));

    expect(await screen.findByRole("alert")).toHaveTextContent("INVALID_CREDENTIALS");
    // No navigation away from login.
    expect(screen.queryByText("HOME")).not.toBeInTheDocument();
  });

  it("renders REGISTRATION_CLOSED on the register tab and keeps the tab visible", async () => {
    await ensureLoggedOut();
    server.use(
      http.post("/api/v1/auth/register", () =>
        HttpResponse.json(
          { detail: { code: "REGISTRATION_CLOSED", message: "REGISTRATION_CLOSED" } },
          { status: 403 },
        ),
      ),
    );

    const user = userEvent.setup();
    renderLogin();
    await screen.findByLabelText(/username/i);

    await user.click(getTab(/^register$/i));
    await user.type(screen.getByLabelText(/username/i), "bob");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(getSubmit(/^register$/i));

    expect(await screen.findByRole("alert")).toHaveTextContent("REGISTRATION_CLOSED");
    expect(getTab(/^register$/i)).toBeInTheDocument();
    expect(screen.queryByText("HOME")).not.toBeInTheDocument();
  });

  it("redirects to / immediately when already authenticated", async () => {
    // Default /auth/me handler returns 200; LoginPage's effect should
    // navigate away before the user sees any form.
    renderLogin();
    await waitFor(() => expect(screen.getByText("HOME")).toBeInTheDocument());
  });
});
