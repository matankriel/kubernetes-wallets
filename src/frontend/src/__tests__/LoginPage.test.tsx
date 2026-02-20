import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import * as authApi from "../api/auth";
import { useAuthStore } from "../store/auth";
import LoginPage from "../pages/LoginPage";

// Mock react-router-dom navigate
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

describe("LoginPage", () => {
  beforeEach(() => {
    useAuthStore.setState({ token: null, claims: null });
    mockNavigate.mockReset();
  });

  it("renders username and password fields", () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("stores token in auth store on successful login", async () => {
    const payload = { sub: "alice", role: "center_admin", scope_id: null, exp: 9999999 };
    const fakeToken = `h.${btoa(JSON.stringify(payload))}.s`;

    vi.spyOn(authApi, "login").mockResolvedValue({
      access_token: fakeToken,
      token_type: "bearer",
      expires_in: 900,
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: "alice" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(useAuthStore.getState().token).toBe(fakeToken);
      expect(useAuthStore.getState().claims?.role).toBe("center_admin");
    });
    expect(mockNavigate).toHaveBeenCalledWith("/");
  });

  it("shows error message on failed login", async () => {
    vi.spyOn(authApi, "login").mockRejectedValue(new Error("Invalid credentials"));

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: "alice" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid credentials");
  });
});
