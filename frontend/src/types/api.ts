/**
 * Shapes mirroring backend response/request types.
 *
 * Kept narrow on purpose — only what the scaffolded flows actually use.
 * Future feature work will extend these alongside their endpoints.
 */

export interface UserResponse {
  id: number;
  username: string;
  is_admin: boolean;
  created_at: string;
}

export interface AuthEnvelope {
  user: UserResponse;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
}

/** Shape of the `detail` payload on a structured error response. */
export interface ApiErrorDetail {
  code: string;
  message: string;
}
