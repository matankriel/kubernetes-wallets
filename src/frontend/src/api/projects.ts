import { apiFetch } from "./client";

export interface Project {
  id: string;
  name: string;
  team_id: string;
  site: string | null;
  sla_type: string | null;
  performance_tier: string | null;
  namespace_name: string | null;
  status: string;
  quota_cpu: number | null;
  quota_ram_gb: number | null;
}

export async function listProjects(): Promise<Project[]> {
  return apiFetch<Project[]>("/api/v1/projects");
}

export async function getProject(id: string): Promise<Project> {
  return apiFetch<Project>(`/api/v1/projects/${id}`);
}

export async function createProject(body: {
  name: string;
  site: string;
  sla_type: string;
  performance_tier: string;
}): Promise<Project> {
  return apiFetch<Project>("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function deleteProject(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/projects/${id}`, { method: "DELETE" });
}
