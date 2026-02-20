import { useQuery } from "@tanstack/react-query";
import { getAllocationTree } from "../../api/allocations";
import type { CenterNode, DeptQuotaNode, FieldNode, TeamQuotaNode } from "../../api/allocations";

function UsageBar({ used, limit, label }: { used: number; limit: number; label: string }) {
  const pct = limit > 0 ? Math.min((used / limit) * 100, 100) : 0;
  return (
    <span style={{ marginLeft: 8, fontSize: 12, color: "#666" }}>
      {label}: {used}/{limit} ({pct.toFixed(0)}%)
    </span>
  );
}

function TeamNode({ team }: { team: TeamQuotaNode }) {
  return (
    <li>
      {team.team_name}
      <UsageBar used={team.cpu_used} limit={team.cpu_limit} label="CPU" />
    </li>
  );
}

function DeptNode({ dept }: { dept: DeptQuotaNode }) {
  return (
    <li>
      <strong>{dept.dept_name}</strong> [{dept.site}]
      <UsageBar used={dept.cpu_used} limit={dept.cpu_limit} label="CPU" />
      <ul>
        {dept.teams.map((t) => (
          <TeamNode key={t.team_id} team={t} />
        ))}
      </ul>
    </li>
  );
}

function FieldNodeComponent({ field }: { field: FieldNode }) {
  return (
    <li>
      <strong>{field.field_name}</strong> [{field.site}] — {field.total_cpu} CPU / {field.total_ram_gb} GB
      <ul>
        {field.departments.map((d) => (
          <DeptNode key={d.dept_id} dept={d} />
        ))}
      </ul>
    </li>
  );
}

function CenterNodeComponent({ center }: { center: CenterNode }) {
  return (
    <li>
      <strong>{center.center_name}</strong>
      <ul>
        {center.fields.map((f) => (
          <FieldNodeComponent key={f.field_id} field={f} />
        ))}
      </ul>
    </li>
  );
}

export default function AllocationTree() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["allocation-tree"],
    queryFn: getAllocationTree,
  });

  if (isLoading) return <p>Loading allocation tree…</p>;
  if (error) return <p role="alert">Failed to load allocation tree.</p>;
  if (!data?.centers.length) return <p>No allocation data available.</p>;

  return (
    <ul>
      {data.centers.map((c) => (
        <CenterNodeComponent key={c.center_id} center={c} />
      ))}
    </ul>
  );
}
