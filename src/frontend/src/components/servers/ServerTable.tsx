import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listServers } from "../../api/servers";

export default function ServerTable() {
  const [site, setSite] = useState("");
  const [tier, setTier] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, error } = useQuery({
    queryKey: ["servers", site, tier, page],
    queryFn: () =>
      listServers({ site: site || undefined, performance_tier: tier || undefined, page }),
  });

  return (
    <div>
      <div style={{ marginBottom: 16, display: "flex", gap: 8 }}>
        <input
          placeholder="Filter by site"
          value={site}
          onChange={(e) => { setSite(e.target.value); setPage(1); }}
        />
        <select value={tier} onChange={(e) => { setTier(e.target.value); setPage(1); }}>
          <option value="">All tiers</option>
          <option value="regular">Regular</option>
          <option value="high_performance">High Performance</option>
        </select>
      </div>

      {isLoading && <p>Loading servers…</p>}
      {error && <p role="alert">Failed to load servers.</p>}

      {data && (
        <>
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Site</th>
                <th>Tier</th>
                <th>CPU</th>
                <th>RAM (GB)</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.data.map((s) => (
                <tr key={s.id}>
                  <td>{s.name}</td>
                  <td>{s.site ?? "—"}</td>
                  <td>{s.performance_tier ?? "—"}</td>
                  <td>{s.cpu ?? "—"}</td>
                  <td>{s.ram_gb ?? "—"}</td>
                  <td>{s.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "center" }}>
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
              Prev
            </button>
            <span>Page {page} — {data.pagination.total} total</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!data.pagination.has_next_page}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
