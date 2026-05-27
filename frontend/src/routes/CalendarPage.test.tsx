import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes, useLocation } from "react-router-dom";

import { CalendarPage } from "@/routes/CalendarPage";
import { server } from "@/test/msw/server";
import { makeCalendarResponse } from "@/test/utils/entries";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

function LocationStub(): JSX.Element {
  const loc = useLocation();
  return (
    <div data-testid="landed-on">
      {loc.pathname}
      {loc.search}
    </div>
  );
}

function renderCalendar(initialEntries: string[] = ["/calendar?year=2026&month=5"]) {
  return renderWithProviders(
    <Routes>
      <Route path="/calendar" element={<CalendarPage />} />
      <Route path="/entries" element={<LocationStub />} />
    </Routes>,
    { initialEntries },
  );
}

describe("CalendarPage", () => {
  it("month nav buttons update the URL", async () => {
    const user = userEvent.setup();
    renderCalendar(["/calendar?year=2026&month=5"]);

    await screen.findByText("May 2026");

    await user.click(screen.getByRole("button", { name: /previous month/i }));
    await waitFor(() => expect(screen.getByText("April 2026")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /next month/i }));
    await waitFor(() => expect(screen.getByText("May 2026")).toBeInTheDocument());
  });

  it("'Today' jumps to the current month", async () => {
    const user = userEvent.setup();
    renderCalendar(["/calendar?year=1990&month=1"]);

    await screen.findByText("January 1990");
    await user.click(screen.getByRole("button", { name: /^today$/i }));

    const now = new Date();
    const monthName = [
      "January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December",
    ][now.getMonth()];
    await waitFor(() =>
      expect(screen.getByText(`${monthName} ${now.getFullYear()}`)).toBeInTheDocument(),
    );
  });

  it("clicking a day with entries navigates to /entries with the date params", async () => {
    server.use(
      http.get("/api/v1/entries/calendar", () =>
        HttpResponse.json(
          makeCalendarResponse({
            year: 2026,
            month: 5,
            days: [{ entry_date: "2026-05-15", count: 2 }],
          }),
          { status: 200 },
        ),
      ),
    );

    const user = userEvent.setup();
    renderCalendar(["/calendar?year=2026&month=5"]);

    await screen.findByTestId("day-badge-2026-05-15");
    await user.click(screen.getByTestId("day-2026-05-15"));

    await waitFor(() => {
      const landed = screen.getByTestId("landed-on");
      expect(landed).toHaveTextContent("/entries");
      expect(landed.textContent).toContain("from_date=2026-05-15");
      expect(landed.textContent).toContain("to_date=2026-05-15");
    });
  });
});
