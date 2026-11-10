import { apiRequest } from "./client";

export async function listComplaints(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return (await apiRequest(`/complaints/${qs ? `?${qs}` : ""}`)).data;
}

export async function getComplaint(id) {
  return (await apiRequest(`/complaints/${id}/`)).data;
}

export async function getComplaintTimeline(id) {
  return (await apiRequest(`/complaints/${id}/timeline/`)).data;
}

export async function createComplaint(formData) {
  return (await apiRequest("/complaints/", { method: "POST", body: formData })).data;
}

export async function uploadComplaintImage(id, formData) {
  return (await apiRequest(`/complaints/${id}/images/`, { method: "POST", body: formData })).data;
}

export async function submitFeedback(id, data) {
  return (await apiRequest(`/complaints/${id}/feedback/`, { method: "POST", body: JSON.stringify(data) })).data;
}

export async function getComplaintAI(id) {
  return (await apiRequest(`/complaints/${id}/ai/`)).data;
}

export async function analyzeComplaint(id) {
  return (await apiRequest(`/complaints/${id}/ai/analyze/`, { method: "POST" })).data;
}

export async function reviewAI(id, data) {
  return (await apiRequest(`/complaints/${id}/ai-review/`, { method: "PATCH", body: JSON.stringify(data) })).data;
}

export async function acceptComplaintAI(id, remarks) {
  return (await apiRequest(`/complaints/${id}/ai/accept/`, { method: "POST", body: JSON.stringify({ remarks }) })).data;
}

export async function assignComplaint(id, engineerId) {
  return (await apiRequest(`/complaints/${id}/assign/`, { method: "POST", body: JSON.stringify({ engineer_id: engineerId }) })).data;
}

export async function reassignComplaint(id, engineerId) {
  return (await apiRequest(`/complaints/${id}/reassign/`, { method: "POST", body: JSON.stringify({ engineer_id: engineerId }) })).data;
}

export async function unassignComplaint(id, remarks = "") {
  return (await apiRequest(`/complaints/${id}/unassign/`, { method: "POST", body: JSON.stringify({ remarks }) })).data;
}

export async function updateComplaintStatus(id, status, remarks) {
  return (await apiRequest(`/complaints/${id}/status/`, { method: "PATCH", body: JSON.stringify({ status, remarks }) })).data;
}

export async function submitResolution(id, data) {
  const body = data instanceof FormData ? data : JSON.stringify(data);
  return (await apiRequest(`/complaints/${id}/resolution/`, { method: "POST", body })).data;
}

export async function verifyResolution(id, approved, remarks) {
  return (await apiRequest(`/complaints/${id}/verify-resolution/`, { method: "POST", body: JSON.stringify({ approved, remarks }) })).data;
}

export async function listComplaintCategories() {
  return (await apiRequest("/complaints/categories/")).data;
}