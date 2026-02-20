/**
 * Auth store — JWT token and decoded claims held in memory only.
 * Never written to localStorage or sessionStorage (air-gap security requirement).
 */

import { create } from "zustand";

export interface Claims {
  sub: string;
  role: string;
  scope_id: string | null;
  exp: number;
}

interface AuthState {
  token: string | null;
  claims: Claims | null;
  setAuth: (token: string, claims: Claims) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  claims: null,
  setAuth: (token, claims) => set({ token, claims }),
  clearAuth: () => set({ token: null, claims: null }),
}));

/** Decode JWT payload without verifying signature (verification is server-side). */
export function decodeToken(token: string): Claims {
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("Invalid JWT");
  const payload = JSON.parse(atob(parts[1]!)) as Claims;
  return payload;
}
