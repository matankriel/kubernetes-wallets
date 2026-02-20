import { useQuery } from "@tanstack/react-query";
import { getAllocationTree } from "../api/allocations";
import { listProjects } from "../api/projects";
import { listServers } from "../api/servers";
import CalculatorWidget from "../components/calculator/CalculatorWidget";

export default function DashboardPage() {
  const { data: servers } = useQuery({
    queryKey: ["servers", "", "", 1],
    queryFn: () => listServers({}),
  });
  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });
  const { data: tree } = useQuery({
    queryKey: ["allocation-tree"],
    queryFn: getAllocationTree,
  });

  const totalServers = servers?.pagination.total ?? 0;
  const activeProjects = projects?.filter((p) => p.status === "active").length ?? 0;

  const allTeams = tree?.centers
    .flatMap((c) => c.fields)
    .flatMap((f) => f.departments)
    .flatMap((d) => d.teams) ?? [];
  const cpuUsed = allTeams.reduce((s, t) => s + t.cpu_used, 0);
  const cpuLimit = allTeams.reduce((s, t) => s + t.cpu_limit, 0);
  const utilPct = cpuLimit > 0 ? ((cpuUsed / cpuLimit) * 100).toFixed(1) : "—";

  return (
    <div>
      <h1>Dashboard</h1>
      <div style={{ display: "flex", gap: 24, marginBottom: 32 }}>
        <div style={{ padding: 16, border: "1px solid #eee" }}>
          <div style={{ fontSize: 32 }}>{totalServers}</div>
          <div>Total Servers</div>
        </div>
        <div style={{ padding: 16, border: "1px solid #eee" }}>
          <div style={{ fontSize: 32 }}>{activeProjects}</div>
          <div>Active Projects</div>
        </div>
        <div style={{ padding: 16, border: "1px solid #eee" }}>
          <div style={{ fontSize: 32 }}>{utilPct}%</div>
          <div>CPU Utilization</div>
        </div>
      </div>
      <CalculatorWidget />
    </div>
  );
}
