import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";

import { AdminPage } from "@/routes/AdminPage";
import { renderWithProviders } from "@/test/utils/renderWithProviders";

function renderAdmin(initialEntries: string[] = ["/admin/users"]) {
  return renderWithProviders(
    <Routes>
      <Route path="/admin" element={<AdminPage />}>
        <Route path="users" element={<div>USERS PANEL</div>} />
        <Route path="settings" element={<div>SETTINGS PANEL</div>} />
      </Route>
    </Routes>,
    { initialEntries },
  );
}

describe("AdminPage", () => {
  it("renders the Users tab by default URL", () => {
    renderAdmin(["/admin/users"]);
    expect(screen.getByText("USERS PANEL")).toBeInTheDocument();
    expect(screen.queryByText("SETTINGS PANEL")).not.toBeInTheDocument();
  });

  it("navigates to the Settings tab when its link is clicked", async () => {
    const user = userEvent.setup();
    renderAdmin(["/admin/users"]);

    await user.click(screen.getByRole("link", { name: /settings/i }));
    expect(screen.getByText("SETTINGS PANEL")).toBeInTheDocument();
    expect(screen.queryByText("USERS PANEL")).not.toBeInTheDocument();
  });
});
