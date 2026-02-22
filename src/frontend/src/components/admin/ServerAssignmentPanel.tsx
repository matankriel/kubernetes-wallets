import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { apiFetch } from "../../api/client";
import { getAllocationTree } from "../../api/allocations";
import { listServers } from "../../api/servers";

export default function ServerAssignmentPanel() {
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const { data: serversData } = useQuery({
    queryKey: ["servers", "", "", 1],
    queryFn: () => listServers({}),
  });

  const { data: tree } = useQuery({
    queryKey: ["allocation-tree"],
    queryFn: getAllocationTree,
  });

  const assignMut = useMutation({
    mutationFn: ({ serverId, fieldId }: { serverId: string; fieldId: string }) =>
      apiFetch<unknown>("/api/v1/allocations/servers", {
        method: "POST",
        body: JSON.stringify({ server_id: serverId, field_id: fieldId }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["servers"] });
      void qc.invalidateQueries({ queryKey: ["allocation-tree"] });
      setError(null);
    },
    onError: (e: Error) => setError(e.message),
  });

  const fields = tree?.centers.flatMap((c) => c.fields) ?? [];

  return (
    <section>
      <h2>Server Assignment</h2>
      <p>Assign unallocated servers to fields.</p>
      {error && <p style={{ color: "red" }}>{error}</p>}

      {serversData?.data.length === 0 && <p>No servers found.</p>}

      <table style={{ borderCollapse: "collapse", width: "100%" }}>
        <thead>
          <tr>
            {["Name", "Site", "Tier", "CPU", "RAM (GB)", "Status", "Assign to Field"].map((h) => (
              <th
                key={h}
                style={{ textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #ccc" }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {serversData?.data.map((server) => (
            <ServerRow
              key={server.id}
              server={server}
              fields={fields}
              onAssign={(fieldId) => assignMut.mutate({ serverId: server.id, fieldId })}
              isPending={assignMut.isPending}
            />
          ))}
        </tbody>
      </table>
    </section>
  );
}

function ServerRow({
  server,
  fields,
  onAssign,
  isPending,
}: {
  server: { id: string; name: string; site: string | null; performance_tier: string | null; cpu: number | null; ram_gb: number | null; status: string };
  fields: Array<{ field_id: string; field_name: string }>;
  onAssign: (fieldId: string) => void;
  isPending: boolean;
}) {
  const [selectedField, setSelectedField] = useState("");

  return (
    <tr>
      <td style={{ padding: "4px 8px" }}>{server.name}</td>
      <td style={{ padding: "4px 8px" }}>{server.site ?? "—"}</td>
      <td style={{ padding: "4px 8px" }}>{server.performance_tier ?? "—"}</td>
      <td style={{ padding: "4px 8px" }}>{server.cpu ?? "—"}</td>
      <td style={{ padding: "4px 8px" }}>{server.ram_gb ?? "—"}</td>
      <td style={{ padding: "4px 8px" }}>{server.status}</td>
      <td style={{ padding: "4px 8px", display: "flex", gap: 4 }}>
        <select value={selectedField} onChange={(e) => setSelectedField(e.target.value)}>
          <option value="">— select field —</option>
          {fields.map((f) => (
            <option key={f.field_id} value={f.field_id}>
              {f.field_name}
            </option>
          ))}
        </select>
        <button
          onClick={() => { if (selectedField) onAssign(selectedField); }}
          disabled={!selectedField || isPending}
        >
          Assign
        </button>
      </td>
    </tr>
  );
}
