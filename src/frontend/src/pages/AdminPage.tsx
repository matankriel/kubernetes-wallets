import { useAuthStore } from "../store/auth";
import OrgHierarchyEditor from "../components/admin/OrgHierarchyEditor";
import ServerAssignmentPanel from "../components/admin/ServerAssignmentPanel";
import UserRoleManager from "../components/admin/UserRoleManager";

export default function AdminPage() {
  const claims = useAuthStore((s) => s.claims);

  if (!claims || claims.role !== "platform_admin") {
    return (
      <div style={{ padding: 24 }}>
        <h1>Access Denied</h1>
        <p>This page is only accessible to platform administrators.</p>
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      <h1>Admin Panel</h1>
      <hr />
      <UserRoleManager />
      <hr style={{ margin: "24px 0" }} />
      <OrgHierarchyEditor />
      <hr style={{ margin: "24px 0" }} />
      <ServerAssignmentPanel />
    </div>
  );
}
