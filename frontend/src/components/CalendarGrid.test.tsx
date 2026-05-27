import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { CalendarGrid } from "@/components/CalendarGrid";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

describe("CalendarGrid", () => {
  it("renders all days for May 2026 (31 days)", () => {
    renderWithProviders(
      <CalendarGrid
        year={2026}
        month={5}
        daysWithEntries={[]}
        today={new Date(2026, 4, 1)}
        onDayClick={vi.fn()}
      />,
    );
    // 31 days in May.
    for (let d = 1; d <= 31; d += 1) {
      const iso = `2026-05-${String(d).padStart(2, "0")}`;
      expect(screen.getByTestId(`day-${iso}`)).toBeInTheDocument();
    }
  });

  it("Feb 2024 has 29 days (leap); Feb 2025 has 28", () => {
    const { unmount } = renderWithProviders(
      <CalendarGrid
        year={2024}
        month={2}
        daysWithEntries={[]}
        today={new Date(2024, 1, 1)}
        onDayClick={vi.fn()}
      />,
    );
    expect(screen.getByTestId("day-2024-02-29")).toBeInTheDocument();
    unmount();

    renderWithProviders(
      <CalendarGrid
        year={2025}
        month={2}
        daysWithEntries={[]}
        today={new Date(2025, 1, 1)}
        onDayClick={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("day-2025-02-29")).not.toBeInTheDocument();
    expect(screen.getByTestId("day-2025-02-28")).toBeInTheDocument();
  });

  it("days with entries render a count badge and are clickable", async () => {
    const onDayClick = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(
      <CalendarGrid
        year={2026}
        month={5}
        daysWithEntries={[
          { entry_date: "2026-05-10", count: 3 },
          { entry_date: "2026-05-20", count: 1 },
        ]}
        today={new Date(2026, 4, 1)}
        onDayClick={onDayClick}
      />,
    );

    expect(screen.getByTestId("day-badge-2026-05-10")).toHaveTextContent("3");
    expect(screen.getByTestId("day-badge-2026-05-20")).toHaveTextContent("1");

    // The cell with entries is a clickable button.
    await user.click(screen.getByTestId("day-2026-05-10"));
    expect(onDayClick).toHaveBeenCalledWith("2026-05-10");
  });

  it("days without entries are not clickable (no day-badge present)", () => {
    renderWithProviders(
      <CalendarGrid
        year={2026}
        month={5}
        daysWithEntries={[]}
        today={new Date(2026, 4, 1)}
        onDayClick={vi.fn()}
      />,
    );
    // No badges anywhere.
    expect(screen.queryByTestId(/day-badge-/)).not.toBeInTheDocument();
    // Day cells exist but are <div>, not <button>.
    const cell = screen.getByTestId("day-2026-05-15");
    expect(cell.tagName).toBe("DIV");
  });

  it("today's marker renders on the correct cell", () => {
    const todayDate = new Date(2026, 4, 27);
    renderWithProviders(
      <CalendarGrid
        year={2026}
        month={5}
        daysWithEntries={[]}
        today={todayDate}
        onDayClick={vi.fn()}
      />,
    );
    const todayCell = screen.getByTestId("day-2026-05-27");
    expect(todayCell.className).toMatch(/ring/);
  });
});
