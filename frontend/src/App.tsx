import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";

import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Layout } from "@/components/Layout";
import { RequireAdmin } from "@/components/RequireAdmin";
import { RequireAuth } from "@/components/RequireAuth";
import { SettingsTab } from "@/components/admin/SettingsTab";
import { UsersTab } from "@/components/admin/UsersTab";
import { AdminPage } from "@/routes/AdminPage";
import { BackupPage } from "@/routes/BackupPage";
import { BibleSearchPage } from "@/routes/BibleSearchPage";
import { CalendarPage } from "@/routes/CalendarPage";
import { DashboardPage } from "@/routes/DashboardPage";
import { EntryDetailPage } from "@/routes/EntryDetailPage";
import { EntryEditPage } from "@/routes/EntryEditPage";
import { EntryListPage } from "@/routes/EntryListPage";
import { EntryNewPage } from "@/routes/EntryNewPage";
import { LoginPage } from "@/routes/LoginPage";
import { NotFoundPage } from "@/routes/NotFoundPage";
import { ReaderPage } from "@/routes/ReaderPage";

const protectedElement = (element: JSX.Element): JSX.Element => (
  <RequireAuth>
    <Layout>{element}</Layout>
  </RequireAuth>
);

const adminElement = (
  <RequireAuth>
    <RequireAdmin>
      <Layout>
        <AdminPage />
      </Layout>
    </RequireAdmin>
  </RequireAuth>
);

const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/", element: protectedElement(<DashboardPage />) },
  { path: "/read", element: protectedElement(<ReaderPage />) },
  { path: "/read/search", element: protectedElement(<BibleSearchPage />) },
  {
    path: "/read/:translationCode/:bookName/:chapterNumber",
    element: protectedElement(<ReaderPage />),
  },
  { path: "/calendar", element: protectedElement(<CalendarPage />) },
  { path: "/backup", element: protectedElement(<BackupPage />) },
  { path: "/entries", element: protectedElement(<EntryListPage />) },
  { path: "/entries/new", element: protectedElement(<EntryNewPage />) },
  { path: "/entries/:entryId", element: protectedElement(<EntryDetailPage />) },
  {
    path: "/entries/:entryId/edit",
    element: protectedElement(<EntryEditPage />),
  },
  {
    path: "/admin",
    element: adminElement,
    children: [
      { index: true, element: <Navigate to="/admin/users" replace /> },
      { path: "users", element: <UsersTab /> },
      { path: "settings", element: <SettingsTab /> },
    ],
  },
  // Unknown paths render the 404 inside the standard Layout when the
  // user is authenticated, so the top bar still appears. Unauth users
  // get redirected to /login by RequireAuth instead.
  { path: "*", element: protectedElement(<NotFoundPage />) },
]);

export function App(): JSX.Element {
  return (
    <ErrorBoundary>
      <RouterProvider router={router} />
    </ErrorBoundary>
  );
}
