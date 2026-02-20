/**
 * Base fetch helper that:
 *  - Attaches Authorization header from the in-memory auth store
 *  - On 401 response, clears auth and redirects to /login
 *  - Throws a typed ApiError on non-2xx responses
 */

import { useAuthStore } from "../store/auth";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = useAuthStore.getState().token;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const resp = await fetch(path, { ...options, headers });

  if (resp.status === 401) {
    useAuthStore.getState().clearAuth();
    window.location.href = "/login";
    throw new ApiError(401, "UNAUTHORIZED", "Session expired");
  }

  if (!resp.ok) {
    const body = (await resp.json().catch(() => ({}))) as {
      error?: { code?: string; message?: string };
    };
    throw new ApiError(
      resp.status,
      body.error?.code ?? "UNKNOWN",
      body.error?.message ?? resp.statusText,
    );
  }

  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}
