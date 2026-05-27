import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { RequireAuth } from "@/components/RequireAuth";
import { DashboardPage } from "@/routes/DashboardPage";
import { LoginPage } from "@/routes/LoginPage";
import { NotFoundPage } from "@/routes/NotFoundPage";

const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    path: "/",
    element: (
      <RequireAuth>
        <Layout>
          <DashboardPage />
        </Layout>
      </RequireAuth>
    ),
  },
  { path: "*", element: <NotFoundPage /> },
]);

export function App(): JSX.Element {
  return <RouterProvider router={router} />;
}
