import { apiFetch } from "./client";

export interface TeamQuotaNode {
  team_id: string;
  team_name: string;
  site: string;
  cpu_limit: number;
  ram_gb_limit: number;
  cpu_used: number;
  ram_gb_used: number;
}

export interface DeptQuotaNode {
  dept_id: string;
  dept_name: string;
  site: string;
  cpu_limit: number;
  ram_gb_limit: number;
  cpu_used: number;
  ram_gb_used: number;
  teams: TeamQuotaNode[];
}

export interface FieldNode {
  field_id: string;
  field_name: string;
  site: string;
  total_cpu: number;
  total_ram_gb: number;
  departments: DeptQuotaNode[];
}

export interface CenterNode {
  center_id: string;
  center_name: string;
  fields: FieldNode[];
}

export interface AllocationTreeResponse {
  centers: CenterNode[];
}

export async function getAllocationTree(): Promise<AllocationTreeResponse> {
  return apiFetch<AllocationTreeResponse>("/api/v1/allocations/tree");
}
