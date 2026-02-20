import { apiFetch } from "./client";

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export async function login(
  username: string,
  password: string,
): Promise<LoginResponse> {
  return apiFetch<LoginResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}
