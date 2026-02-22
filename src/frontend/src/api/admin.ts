import { apiFetch } from "./client";

// ── Types ──────────────────────────────────────────────────────────────────────

export interface UserRoleResponse {
  id: string;
  username: string;
  role: string;
  scope_id: string | null;
  assigned_by: string;
  assigned_at: string | null;
}

export interface UpsertUserRoleRequest {
  username: string;
  role: string;
  scope_id: string | null;
}

export interface CenterResponse {
  id: string;
  name: string;
}

export interface FieldResponse {
  id: string;
  center_id: string;
  name: string;
  site: string;
}

export interface DepartmentResponse {
  id: string;
  field_id: string;
  name: string;
}

export interface TeamResponse {
  id: string;
  department_id: string;
  name: string;
  ldap_group_cn: string | null;
}

// ── User role endpoints ────────────────────────────────────────────────────────

export async function listUserRoles(): Promise<UserRoleResponse[]> {
  return apiFetch<UserRoleResponse[]>("/api/v1/admin/user-roles");
}

export async function upsertUserRole(body: UpsertUserRoleRequest): Promise<UserRoleResponse> {
  return apiFetch<UserRoleResponse>("/api/v1/admin/user-roles", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function deleteUserRole(username: string): Promise<void> {
  await apiFetch<void>(`/api/v1/admin/user-roles/${encodeURIComponent(username)}`, {
    method: "DELETE",
  });
}

// ── Center endpoints ───────────────────────────────────────────────────────────

export async function createCenter(body: { name: string }): Promise<CenterResponse> {
  return apiFetch<CenterResponse>("/api/v1/admin/org/centers", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateCenter(id: string, body: { name: string }): Promise<CenterResponse> {
  return apiFetch<CenterResponse>(`/api/v1/admin/org/centers/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteCenter(id: string): Promise<void> {
  await apiFetch<void>(`/api/v1/admin/org/centers/${id}`, { method: "DELETE" });
}

// ── Field endpoints ────────────────────────────────────────────────────────────

export async function createField(body: {
  center_id: string;
  name: string;
  site: string;
}): Promise<FieldResponse> {
  return apiFetch<FieldResponse>("/api/v1/admin/org/fields", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateField(
  id: string,
  body: { name: string; site: string },
): Promise<FieldResponse> {
  return apiFetch<FieldResponse>(`/api/v1/admin/org/fields/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteField(id: string): Promise<void> {
  await apiFetch<void>(`/api/v1/admin/org/fields/${id}`, { method: "DELETE" });
}

// ── Department endpoints ───────────────────────────────────────────────────────

export async function createDepartment(body: {
  field_id: string;
  name: string;
}): Promise<DepartmentResponse> {
  return apiFetch<DepartmentResponse>("/api/v1/admin/org/departments", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateDepartment(
  id: string,
  body: { name: string },
): Promise<DepartmentResponse> {
  return apiFetch<DepartmentResponse>(`/api/v1/admin/org/departments/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteDepartment(id: string): Promise<void> {
  await apiFetch<void>(`/api/v1/admin/org/departments/${id}`, { method: "DELETE" });
}

// ── Team endpoints ─────────────────────────────────────────────────────────────

export async function createTeam(body: {
  department_id: string;
  name: string;
  ldap_group_cn?: string | null;
}): Promise<TeamResponse> {
  return apiFetch<TeamResponse>("/api/v1/admin/org/teams", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateTeam(
  id: string,
  body: { name: string; ldap_group_cn?: string | null },
): Promise<TeamResponse> {
  return apiFetch<TeamResponse>(`/api/v1/admin/org/teams/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteTeam(id: string): Promise<void> {
  await apiFetch<void>(`/api/v1/admin/org/teams/${id}`, { method: "DELETE" });
}
