import { apiRequest } from "./client";

export async function getOverview() {
  return (await apiRequest("/analytics/overview/")).data;
}

export async function getComplaintCategories() {
  return (await apiRequest("/analytics/complaints/categories/")).data;
}

export async function getComplaintDepartments() {
  return (await apiRequest("/analytics/complaints/departments/")).data;
}

export async function getComplaintWards() {
  return (await apiRequest("/analytics/complaints/wards/")).data;
}

export async function getComplaintTrends() {
  return (await apiRequest("/analytics/complaints/trends/")).data;
}

export async function getMapComplaints() {
  return (await apiRequest("/analytics/map/complaints/")).data;
}

export async function getHeatmap() {
  return (await apiRequest("/analytics/map/heatmap/")).data;
}