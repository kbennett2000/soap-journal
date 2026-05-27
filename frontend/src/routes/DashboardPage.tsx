import { useAuth } from "@/hooks/useAuth";

export function DashboardPage(): JSX.Element {
  const { user } = useAuth();
  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-semibold">Welcome, {user?.username ?? "friend"}.</h1>
      <p className="text-slate-600 dark:text-slate-300">
        Dashboard coming soon. For now, the foundation works.
      </p>
    </div>
  );
}
