import { useState } from "react";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { useAuth } from "@/hooks/useAuth";
import {
  useAdminCreateUser,
  useAdminDeleteUser,
  useAdminDemoteUser,
  useAdminPromoteUser,
  useAdminResetPassword,
  useAdminUsers,
} from "@/hooks/useAdmin";
import { ApiError } from "@/lib/apiError";
import type { UserResponse } from "@/types/api";

type Banner = { tone: "error" | "success"; text: string } | null;

function formatDate(iso: string): string {
  // The backend hands us ISO strings; we render a YYYY-MM-DD slice to
  // avoid timezone-dependent display drift in tests.
  return iso.slice(0, 10);
}

function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) return err.message;
  return fallback;
}

export function UsersTab(): JSX.Element {
  const { user: currentUser } = useAuth();
  const usersQuery = useAdminUsers();
  const createMutation = useAdminCreateUser();
  const deleteMutation = useAdminDeleteUser();
  const resetMutation = useAdminResetPassword();
  const promoteMutation = useAdminPromoteUser();
  const demoteMutation = useAdminDemoteUser();

  const [banner, setBanner] = useState<Banner>(null);
  const [creating, setCreating] = useState(false);
  const [resetTarget, setResetTarget] = useState<UserResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<UserResponse | null>(null);

  if (usersQuery.isLoading) {
    return (
      <div data-testid="users-loading" className="space-y-2">
        <div className="h-9 w-32 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
        <div className="h-32 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
      </div>
    );
  }

  if (usersQuery.isError) {
    return (
      <div
        role="alert"
        className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200"
      >
        Unable to load users.
      </div>
    );
  }

  const users = usersQuery.data?.users ?? [];

  async function handleDelete(): Promise<void> {
    if (!deleteTarget) return;
    setBanner(null);
    try {
      await deleteMutation.mutateAsync(deleteTarget.id);
      setBanner({ tone: "success", text: `Deleted ${deleteTarget.username}.` });
      setDeleteTarget(null);
    } catch (err) {
      setBanner({
        tone: "error",
        text: errorMessage(err, "Unable to delete user."),
      });
      setDeleteTarget(null);
    }
  }

  async function handlePromote(user: UserResponse): Promise<void> {
    setBanner(null);
    try {
      await promoteMutation.mutateAsync(user.id);
      setBanner({ tone: "success", text: `Promoted ${user.username}.` });
    } catch (err) {
      setBanner({
        tone: "error",
        text: errorMessage(err, "Unable to promote user."),
      });
    }
  }

  async function handleDemote(user: UserResponse): Promise<void> {
    setBanner(null);
    try {
      await demoteMutation.mutateAsync(user.id);
      setBanner({ tone: "success", text: `Demoted ${user.username}.` });
    } catch (err) {
      setBanner({
        tone: "error",
        text: errorMessage(err, "Unable to demote user."),
      });
    }
  }

  return (
    <div className="space-y-4">
      {banner && (
        <div
          role="alert"
          data-testid={`users-banner-${banner.tone}`}
          className={
            banner.tone === "error"
              ? "rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200"
              : "rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
          }
        >
          {banner.text}
        </div>
      )}

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Users</h2>
        <button
          type="button"
          onClick={() => setCreating(true)}
          className="inline-flex h-9 items-center rounded-md bg-slate-900 px-3 text-sm font-medium text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
        >
          New user
        </button>
      </div>

      <div className="overflow-x-auto rounded-md border border-slate-200 dark:border-slate-800">
        <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-800">
          <thead className="bg-slate-50 dark:bg-slate-900">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-slate-600 dark:text-slate-300">
                Username
              </th>
              <th className="px-3 py-2 text-left font-medium text-slate-600 dark:text-slate-300">
                Admin
              </th>
              <th className="px-3 py-2 text-left font-medium text-slate-600 dark:text-slate-300">
                Created
              </th>
              <th className="px-3 py-2 text-right font-medium text-slate-600 dark:text-slate-300">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white dark:divide-slate-800 dark:bg-slate-950">
            {users.map((u) => {
              const isMe = currentUser?.id === u.id;
              return (
                <tr key={u.id} data-testid={`user-row-${u.id}`}>
                  <td className="px-3 py-2 text-slate-900 dark:text-slate-100">
                    {u.username}
                    {isMe && (
                      <span className="ml-1 text-xs text-slate-500 dark:text-slate-400">
                        (you)
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-slate-700 dark:text-slate-200">
                    {u.is_admin ? (
                      <span aria-label="admin">✓</span>
                    ) : (
                      <span className="text-slate-400 dark:text-slate-600">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-slate-600 dark:text-slate-300">
                    {formatDate(u.created_at)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <div className="flex justify-end gap-1">
                      <button
                        type="button"
                        onClick={() => setResetTarget(u)}
                        className="inline-flex h-8 items-center rounded-md border border-slate-300 bg-white px-2 text-xs font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                      >
                        Reset password
                      </button>
                      {u.is_admin ? (
                        <button
                          type="button"
                          onClick={() => {
                            void handleDemote(u);
                          }}
                          disabled={demoteMutation.isPending}
                          className="inline-flex h-8 items-center rounded-md border border-slate-300 bg-white px-2 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                        >
                          Demote
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => {
                            void handlePromote(u);
                          }}
                          disabled={promoteMutation.isPending}
                          className="inline-flex h-8 items-center rounded-md border border-slate-300 bg-white px-2 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                        >
                          Promote
                        </button>
                      )}
                      {!isMe && (
                        <button
                          type="button"
                          onClick={() => setDeleteTarget(u)}
                          className="inline-flex h-8 items-center rounded-md border border-rose-300 bg-white px-2 text-xs font-medium text-rose-700 hover:bg-rose-50 dark:border-rose-800 dark:bg-slate-900 dark:text-rose-300 dark:hover:bg-rose-950"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <CreateUserDialog
        open={creating}
        onClose={() => setCreating(false)}
        onCreated={(u) => {
          setBanner({ tone: "success", text: `Created ${u.username}.` });
          setCreating(false);
        }}
        createMutation={createMutation}
      />

      <ResetPasswordDialog
        target={resetTarget}
        onClose={() => setResetTarget(null)}
        onReset={(u) => {
          setBanner({
            tone: "success",
            text: `Password reset for ${u.username}.`,
          });
          setResetTarget(null);
        }}
        resetMutation={resetMutation}
      />

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete user"
        message={
          deleteTarget
            ? `Delete ${deleteTarget.username}? Their entries will also be removed. This cannot be undone.`
            : ""
        }
        confirmLabel={deleteMutation.isPending ? "Deleting…" : "Delete"}
        destructive
        onConfirm={() => {
          void handleDelete();
        }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

interface CreateUserDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: (user: UserResponse) => void;
  createMutation: ReturnType<typeof useAdminCreateUser>;
}

function CreateUserDialog({
  open,
  onClose,
  onCreated,
  createMutation,
}: CreateUserDialogProps): JSX.Element | null {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  function reset(): void {
    setUsername("");
    setPassword("");
    setIsAdmin(false);
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    setError(null);
    try {
      const created = await createMutation.mutateAsync({
        username: username.trim(),
        password,
        is_admin: isAdmin,
      });
      reset();
      onCreated(created);
    } catch (err) {
      setError(errorMessage(err, "Unable to create user."));
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-user-title"
      data-testid="create-user-dialog"
      className="fixed inset-0 z-20 flex items-center justify-center bg-slate-900/40 p-4"
    >
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-3 rounded-lg bg-white p-5 shadow-xl dark:bg-slate-900"
      >
        <h3
          id="create-user-title"
          className="text-base font-semibold text-slate-900 dark:text-slate-100"
        >
          New user
        </h3>

        <div className="space-y-1">
          <label
            htmlFor="new-user-username"
            className="block text-xs font-medium text-slate-600 dark:text-slate-300"
          >
            Username
          </label>
          <input
            id="new-user-username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            minLength={3}
            maxLength={32}
            pattern="[A-Za-z0-9_\-]+"
            className="block h-9 w-full rounded-md border border-slate-300 bg-white px-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          />
        </div>

        <div className="space-y-1">
          <label
            htmlFor="new-user-password"
            className="block text-xs font-medium text-slate-600 dark:text-slate-300"
          >
            Password
          </label>
          <input
            id="new-user-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            className="block h-9 w-full rounded-md border border-slate-300 bg-white px-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          />
        </div>

        <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
          <input
            type="checkbox"
            checked={isAdmin}
            onChange={(e) => setIsAdmin(e.target.checked)}
          />
          Admin
        </label>

        {error && (
          <p
            role="alert"
            className="text-xs text-rose-700 dark:text-rose-300"
          >
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={() => {
              reset();
              onClose();
            }}
            className="inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="inline-flex h-9 items-center rounded-md bg-slate-900 px-3 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
          >
            {createMutation.isPending ? "Creating…" : "Create"}
          </button>
        </div>
      </form>
    </div>
  );
}

interface ResetPasswordDialogProps {
  target: UserResponse | null;
  onClose: () => void;
  onReset: (user: UserResponse) => void;
  resetMutation: ReturnType<typeof useAdminResetPassword>;
}

function ResetPasswordDialog({
  target,
  onClose,
  onReset,
  resetMutation,
}: ResetPasswordDialogProps): JSX.Element | null {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!target) return null;

  async function handleSubmit(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    if (!target) return;
    setError(null);
    try {
      await resetMutation.mutateAsync({
        userId: target.id,
        newPassword: password,
      });
      setPassword("");
      onReset(target);
    } catch (err) {
      setError(errorMessage(err, "Unable to reset password."));
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="reset-password-title"
      data-testid="reset-password-dialog"
      className="fixed inset-0 z-20 flex items-center justify-center bg-slate-900/40 p-4"
    >
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-3 rounded-lg bg-white p-5 shadow-xl dark:bg-slate-900"
      >
        <h3
          id="reset-password-title"
          className="text-base font-semibold text-slate-900 dark:text-slate-100"
        >
          Reset password for {target.username}
        </h3>
        <p className="text-xs text-slate-600 dark:text-slate-300">
          All of this user&apos;s sessions will be terminated.
        </p>

        <div className="space-y-1">
          <label
            htmlFor="reset-password-input"
            className="block text-xs font-medium text-slate-600 dark:text-slate-300"
          >
            New password
          </label>
          <input
            id="reset-password-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            className="block h-9 w-full rounded-md border border-slate-300 bg-white px-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          />
        </div>

        {error && (
          <p
            role="alert"
            className="text-xs text-rose-700 dark:text-rose-300"
          >
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={() => {
              setPassword("");
              setError(null);
              onClose();
            }}
            className="inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={resetMutation.isPending}
            className="inline-flex h-9 items-center rounded-md bg-slate-900 px-3 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
          >
            {resetMutation.isPending ? "Saving…" : "Reset"}
          </button>
        </div>
      </form>
    </div>
  );
}
