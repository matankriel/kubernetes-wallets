import { Outlet, useNavigate } from "react-router-dom";
import { useAuthStore } from "../../store/auth";
import Sidebar from "./Sidebar";

export default function Layout() {
  const navigate = useNavigate();
  const { claims, clearAuth } = useAuthStore();

  if (!claims) {
    navigate("/login", { replace: true });
    return null;
  }

  const handleLogout = () => {
    clearAuth();
    navigate("/login", { replace: true });
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <header style={{ padding: "8px 16px", borderBottom: "1px solid #ccc", display: "flex", justifyContent: "flex-end" }}>
          <button onClick={handleLogout}>Logout</button>
        </header>
        <main style={{ flex: 1, padding: 24 }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
