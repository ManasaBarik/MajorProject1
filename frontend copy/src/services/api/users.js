import { apiRequest } from "./client";

export async function listUsers() {
  return (await apiRequest("/users/")).data;
}

export async function createDepartmentStaff(data) {
  return (await apiRequest("/auth/register/", { method: "POST", body: JSON.stringify(data) })).data;
}

export async function updateOfficer(id, data) {
  return (await apiRequest(`/admin/officers/${id}/`, { method: "PATCH", body: JSON.stringify(data) })).data;
}

export async function listOfficers() {
  return (await apiRequest("/admin/officers/")).data;
}

export async function listEngineers() {
  return (await apiRequest("/admin/engineers/")).data;
}

export async function updateEngineer(id, data) {
  return (await apiRequest(`/admin/engineers/${id}/`, { method: "PATCH", body: JSON.stringify(data) })).data;
}

export async function listAuditLogs() {
  return (await apiRequest("/audit-logs/")).data;
}