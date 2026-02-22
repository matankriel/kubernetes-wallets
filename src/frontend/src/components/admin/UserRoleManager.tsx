import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  deleteUserRole,
  listUserRoles,
  upsertUserRole,
  type UpsertUserRoleRequest,
} from "../../api/admin";

const ASSIGNABLE_ROLES = ["platform_admin", "field_admin", "dept_admin", "team_lead"] as const;

export default function UserRoleManager() {
  const qc = useQueryClient();
  const { data: roles, isLoading } = useQuery({
    queryKey: ["user-roles"],
    queryFn: listUserRoles,
  });

  const [username, setUsername] = useState("");
  const [role, setRole] = useState<string>("field_admin");
  const [scopeId, setScopeId] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const upsertMutation = useMutation({
    mutationFn: (body: UpsertUserRoleRequest) => upsertUserRole(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["user-roles"] });
      setUsername("");
      setScopeId("");
      setFormError(null);
    },
    onError: (err: Error) => setFormError(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteUserRole,
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["user-roles"] }),
  });

  const handleGrant = () => {
    if (!username.trim()) {
      setFormError("Username is required");
      return;
    }
    setFormError(null);
    upsertMutation.mutate({
      username: username.trim(),
      role,
      scope_id: scopeId.trim() || null,
    });
  };

  return (
    <section>
      <h2>User Role Overrides</h2>

      <div style={{ marginBottom: 16 }}>
        <h3>Grant / Update Role</h3>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
          <label>
            Username
            <br />
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="alice"
            />
          </label>
          <label>
            Role
            <br />
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              {ASSIGNABLE_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
          <label>
            Scope ID (leave blank for platform_admin)
            <br />
            <input
              value={scopeId}
              onChange={(e) => setScopeId(e.target.value)}
              placeholder="field/dept/team UUID"
            />
          </label>
          <button onClick={handleGrant} disabled={upsertMutation.isPending}>
            {upsertMutation.isPending ? "Saving…" : "Grant Role"}
          </button>
        </div>
        {formError && <p style={{ color: "red" }}>{formError}</p>}
      </div>

      {isLoading && <p>Loading…</p>}
      {roles && roles.length === 0 && <p>No DB role overrides.</p>}
      {roles && roles.length > 0 && (
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              {["Username", "Role", "Scope ID", "Assigned By", "Assigned At", ""].map((h) => (
                <th key={h} style={{ textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #ccc" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {roles.map((r) => (
              <tr key={r.username}>
                <td style={{ padding: "4px 8px" }}>{r.username}</td>
                <td style={{ padding: "4px 8px" }}>{r.role}</td>
                <td style={{ padding: "4px 8px" }}>{r.scope_id ?? "—"}</td>
                <td style={{ padding: "4px 8px" }}>{r.assigned_by}</td>
                <td style={{ padding: "4px 8px" }}>{r.assigned_at ?? "—"}</td>
                <td style={{ padding: "4px 8px" }}>
                  <button
                    onClick={() => {
                      if (window.confirm(`Revoke role for ${r.username}?`)) {
                        deleteMutation.mutate(r.username);
                      }
                    }}
                    disabled={deleteMutation.isPending}
                  >
                    Revoke
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
