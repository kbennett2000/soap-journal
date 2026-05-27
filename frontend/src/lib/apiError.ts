/**
 * Single error type for the API client.
 *
 * `status` is the HTTP status (0 for network errors), `code` is the
 * structured backend error code from `core/errors.py`, and `message` is
 * the human-readable detail message. Catch blocks check `code` to
 * branch on specific failures and fall back to `message` for display.
 */
export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}
