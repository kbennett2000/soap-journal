import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { RequireAuth } from "@/components/RequireAuth";
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

const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/", element: protectedElement(<DashboardPage />) },
  { path: "/read", element: protectedElement(<ReaderPage />) },
  {
    path: "/read/:translationCode/:bookName/:chapterNumber",
    element: protectedElement(<ReaderPage />),
  },
  { path: "/entries", element: protectedElement(<EntryListPage />) },
  { path: "/entries/new", element: protectedElement(<EntryNewPage />) },
  { path: "/entries/:entryId", element: protectedElement(<EntryDetailPage />) },
  {
    path: "/entries/:entryId/edit",
    element: protectedElement(<EntryEditPage />),
  },
  { path: "*", element: <NotFoundPage /> },
]);

export function App(): JSX.Element {
  return <RouterProvider router={router} />;
}
