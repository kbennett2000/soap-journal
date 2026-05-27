import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Top-level error boundary. Catches render-time errors in any descendant
 * and shows a friendly fallback so the app never goes fully white. We
 * deliberately don't pipe to any third-party telemetry — the
 * self-hosted constraint stands. Operators can read the browser console
 * if they need a stack.
 */
export class ErrorBoundary extends Component<Props, State> {
  override state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("ErrorBoundary caught:", error, info.componentStack);
  }

  handleReset = (): void => {
    this.setState({ error: null });
  };

  override render(): ReactNode {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-6 py-12 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
        <div className="w-full max-w-md space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h1 className="text-2xl font-semibold">Something went wrong</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            The page hit an unexpected error. Try reloading, or head back to the
            dashboard.
          </p>
          <details className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
            <summary className="cursor-pointer font-medium">
              Error details
            </summary>
            <pre className="mt-2 whitespace-pre-wrap break-words">
              {error.message || String(error)}
            </pre>
          </details>
          <div className="flex flex-wrap gap-2">
            <a
              href="/"
              onClick={this.handleReset}
              className="inline-flex h-9 items-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white shadow-sm hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
            >
              Go to dashboard
            </a>
            <button
              type="button"
              onClick={() => {
                this.handleReset();
                window.location.reload();
              }}
              className="inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              Reload page
            </button>
          </div>
        </div>
      </div>
    );
  }
}
