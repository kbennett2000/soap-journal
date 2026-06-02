import { ApiError } from "@/lib/apiError";
import type { ApiErrorDetail } from "@/types/api";

const API_PREFIX = "/api/v1";

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

interface ApiOptions<TBody> {
  body?: TBody;
  query?: Record<string, string | number | boolean | undefined | null>;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: ApiOptions<unknown>["query"]): string {
  const base = `${API_PREFIX}${path}`;
  if (!query) return base;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) continue;
    params.append(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${base}?${qs}` : base;
}

function isApiErrorDetail(value: unknown): value is ApiErrorDetail {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return typeof candidate.code === "string" && typeof candidate.message === "string";
}

async function readError(response: Response): Promise<ApiError> {
  let detail: ApiErrorDetail | undefined;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (isApiErrorDetail(body.detail)) {
      detail = body.detail;
    }
  } catch {
    // Body wasn't JSON or was unreadable; fall through to default message.
  }
  const code = detail?.code ?? `HTTP_${response.status}`;
  const message = detail?.message ?? response.statusText ?? "Request failed";
  return new ApiError(response.status, code, message);
}

/**
 * Typed `fetch` wrapper.
 *
 * - Prefixes paths with /api/v1 (callers pass "/auth/login", not the full URL).
 * - Sends the session cookie (`credentials: "include"`).
 * - Throws ApiError on non-2xx — `status`, `code`, and `message` come from
 *   `{ detail: { code, message } }` per backend convention.
 * - 204 resolves to `undefined as TResponse`.
 * - Network failures throw ApiError(0, "NETWORK_ERROR", ...).
 *
 * No runtime schema validation in here — callers Zod-parse the response
 * when the shape is genuinely uncertain (form input, third-party data).
 */
export async function apiRequest<TResponse, TBody = unknown>(
  method: Method,
  path: string,
  options: ApiOptions<TBody> = {},
): Promise<TResponse> {
  const init: RequestInit = {
    method,
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
    signal: options.signal,
  };
  if (options.body !== undefined) {
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
    init.body = JSON.stringify(options.body);
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query), init);
  } catch (err) {
    throw new ApiError(0, "NETWORK_ERROR", (err as Error).message || "Network error");
  }

  if (!response.ok) {
    throw await readError(response);
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }
  return (await response.json()) as TResponse;
}
