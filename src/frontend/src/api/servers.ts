import { apiFetch } from "./client";

export interface Server {
  id: string;
  name: string;
  vendor: string | null;
  site: string | null;
  deployment_cluster: string | null;
  cpu: number | null;
  ram_gb: number | null;
  performance_tier: string | null;
  status: string;
}

export interface ServerListResponse {
  data: Server[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    has_next_page: boolean;
  };
}

export async function listServers(params: {
  site?: string;
  performance_tier?: string;
  page?: number;
  page_size?: number;
}): Promise<ServerListResponse> {
  const qs = new URLSearchParams();
  if (params.site) qs.set("site", params.site);
  if (params.performance_tier) qs.set("performance_tier", params.performance_tier);
  if (params.page) qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));
  return apiFetch<ServerListResponse>(`/api/v1/servers?${qs.toString()}`);
}
