import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listProjects } from "../api/projects";
import ProjectWizard from "../components/projects/ProjectWizard";
import { useAuthStore } from "../store/auth";

const STATUS_COLORS: Record<string, string> = {
  provisioning: "goldenrod",
  active: "green",
  failed: "red",
  deleting: "grey",
};

export default function ProjectsPage() {
  const claims = useAuthStore((s) => s.claims);
  const [showWizard, setShowWizard] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>Projects</h1>
        {claims?.role === "team_lead" && (
          <button onClick={() => setShowWizard(true)}>New Project</button>
        )}
      </div>

      {showWizard && <ProjectWizard onClose={() => setShowWizard(false)} />}

      {isLoading && <p>Loading projects…</p>}
      {error && <p role="alert">Failed to load projects.</p>}

      {data && (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Site</th>
              <th>SLA</th>
              <th>Tier</th>
              <th>Namespace</th>
              <th>Status</th>
              <th>CPU</th>
            </tr>
          </thead>
          <tbody>
            {data.map((p) => (
              <tr key={p.id}>
                <td>{p.name}</td>
                <td>{p.site ?? "—"}</td>
                <td>{p.sla_type ?? "—"}</td>
                <td>{p.performance_tier ?? "—"}</td>
                <td>{p.namespace_name ?? "—"}</td>
                <td>
                  <span style={{ color: STATUS_COLORS[p.status] ?? "black" }}>
                    {p.status}
                  </span>
                </td>
                <td>{p.quota_cpu ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
