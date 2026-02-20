import { describe, it, expect, beforeEach } from "vitest";
import { useAuthStore, decodeToken } from "../store/auth";

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.setState({ token: null, claims: null });
  });

  it("starts with no token and no claims", () => {
    const { token, claims } = useAuthStore.getState();
    expect(token).toBeNull();
    expect(claims).toBeNull();
  });

  it("setAuth stores token and claims", () => {
    const claims = { sub: "alice", role: "center_admin", scope_id: null, exp: 9999 };
    useAuthStore.getState().setAuth("my-token", claims);
    const state = useAuthStore.getState();
    expect(state.token).toBe("my-token");
    expect(state.claims).toEqual(claims);
  });

  it("clearAuth resets token and claims to null", () => {
    const claims = { sub: "alice", role: "center_admin", scope_id: null, exp: 9999 };
    useAuthStore.getState().setAuth("my-token", claims);
    useAuthStore.getState().clearAuth();
    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.claims).toBeNull();
  });
});

describe("decodeToken", () => {
  it("decodes a valid JWT payload", () => {
    // Build a fake JWT: header.payload.signature (signature not verified client-side)
    const payload = { sub: "alice", role: "center_admin", scope_id: null, exp: 9999999 };
    const encoded = btoa(JSON.stringify(payload));
    const token = `header.${encoded}.sig`;
    const decoded = decodeToken(token);
    expect(decoded.sub).toBe("alice");
    expect(decoded.role).toBe("center_admin");
  });

  it("throws on malformed token", () => {
    expect(() => decodeToken("invalid")).toThrow();
  });
});
