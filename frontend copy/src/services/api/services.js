import { apiRequest } from "./client";

export async function listServices() {
  return (await apiRequest("/services/")).data;
}

export async function getService(id) {
  return (await apiRequest(`/services/${id}/`)).data;
}

export async function createService(data) {
  return (await apiRequest("/services/", { method: "POST", body: JSON.stringify(data) })).data;
}

export async function updateService(id, data) {
  return (await apiRequest(`/services/${id}/`, { method: "PATCH", body: JSON.stringify(data) })).data;
}

export async function deleteService(id) {
  return (await apiRequest(`/services/${id}/`, { method: "DELETE" }));
}

export async function listDepartments() {
  return (await apiRequest("/departments/")).data;
}

export async function getDepartment(id) {
  return (await apiRequest(`/departments/${id}/`)).data;
}

export async function getDepartmentStaff(id) {
  return (await apiRequest(`/departments/${id}/staff/`)).data;
}

export async function createDepartment(data) {
  return (await apiRequest("/departments/", { method: "POST", body: JSON.stringify(data) })).data;
}

export async function updateDepartment(id, data) {
  return (await apiRequest(`/departments/${id}/`, { method: "PATCH", body: JSON.stringify(data) })).data;
}

export async function deleteDepartment(id) {
  return (await apiRequest(`/departments/${id}/`, { method: "DELETE" }));
}