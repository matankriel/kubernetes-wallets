import { Link } from "react-router-dom";
import { useAuthStore } from "../../store/auth";

const NAV_ITEMS = [
  { label: "Dashboard", to: "/", roles: ["center_admin", "field_admin", "dept_admin", "team_lead"] },
  { label: "Servers", to: "/servers", roles: ["center_admin", "field_admin"] },
  { label: "Allocations", to: "/allocations", roles: ["center_admin", "field_admin", "dept_admin"] },
  { label: "Projects", to: "/projects", roles: ["center_admin", "field_admin", "dept_admin", "team_lead"] },
] as const;

export default function Sidebar() {
  const claims = useAuthStore((s) => s.claims);
  if (!claims) return null;

  const visibleItems = NAV_ITEMS.filter((item) =>
    (item.roles as readonly string[]).includes(claims.role),
  );

  return (
    <nav style={{ width: 200, padding: 16, borderRight: "1px solid #ccc" }}>
      <div style={{ marginBottom: 16, fontWeight: "bold" }}>InfraHub</div>
      <div style={{ marginBottom: 16, fontSize: 12, color: "#666" }}>
        {claims.sub} ({claims.role})
      </div>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {visibleItems.map((item) => (
          <li key={item.to} style={{ marginBottom: 8 }}>
            <Link to={item.to}>{item.label}</Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
