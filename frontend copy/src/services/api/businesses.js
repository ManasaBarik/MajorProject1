import { apiRequest } from "./client";

export async function listBusinesses() {
  return (await apiRequest("/businesses/")).data;
}

export async function getBusiness(id) {
  return (await apiRequest(`/businesses/${id}/`)).data;
}

export async function createBusiness(data) {
  return (await apiRequest("/businesses/", { method: "POST", body: JSON.stringify(data) })).data;
}

export async function updateBusiness(id, data) {
  return (await apiRequest(`/businesses/${id}/`, { method: "PATCH", body: JSON.stringify(data) })).data;
}