import { apiDownload, apiRequest } from "./client";

export async function listApplications(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return (await apiRequest(`/applications/${qs ? `?${qs}` : ""}`)).data;
}

export async function getApplication(id) {
  return (await apiRequest(`/applications/${id}/`)).data;
}

export async function downloadApplicationDocument(id, documentId) {
  return apiDownload(`/applications/${id}/documents/${documentId}/download/`);
}

export async function downloadApplicationCertificate(id) {
  return apiDownload(`/applications/${id}/certificate/`);
}

export async function createApplication(data) {
  const body = data instanceof FormData ? data : JSON.stringify(data);
  return (await apiRequest("/applications/", { method: "POST", body })).data;
}

export async function updateApplication(id, data) {
  return (await apiRequest(`/applications/${id}/`, { method: "PATCH", body: JSON.stringify(data) })).data;
}

export async function submitApplication(id) {
  return (await apiRequest(`/applications/${id}/submit/`, { method: "POST" })).data;
}

export async function getApplicationDocuments(id) {
  return (await apiRequest(`/applications/${id}/documents/`)).data;
}

export async function uploadApplicationDocument(id, formData) {
  return (await apiRequest(`/applications/${id}/documents/`, { method: "POST", body: formData })).data;
}

export async function verifyApplicationDocument(id, documentId, data) {
  return (await apiRequest(`/applications/${id}/documents/${documentId}/verify/`, { method: "PATCH", body: JSON.stringify(data) })).data;
}

export async function getApplicationTimeline(id) {
  return (await apiRequest(`/applications/${id}/timeline/`)).data;
}

export async function listAssignedApplications() {
  return (await apiRequest("/applications/assigned/")).data;
}

export async function listEligibleApplicationEngineers(id) {
  return (await apiRequest(`/applications/${id}/eligible-engineers/`)).data;
}

export async function assignApplicationEngineer(id, engineerProfileId, remarks = "") {
  return (await apiRequest(`/applications/${id}/assign-engineer/`, {
    method: "POST",
    body: JSON.stringify({ engineer_profile_id: engineerProfileId, remarks }),
  })).data;
}

export async function completeEngineerReview(id, remarks = "") {
  return (await apiRequest(`/applications/${id}/complete-engineer-review/`, {
    method: "POST",
    body: JSON.stringify({ remarks }),
  })).data;
}

export async function reviewApplication(id, data) {
  return (await apiRequest(`/applications/${id}/review/`, { method: "POST", body: JSON.stringify(data) })).data;
}

export async function requestClarification(id, data) {
  return (await apiRequest(`/applications/${id}/clarification/`, { method: "POST", body: JSON.stringify(data) })).data;
}

export async function updateApplicationStatus(id, status, remarks = "") {
  return (await apiRequest(`/applications/${id}/status/`, { method: "PATCH", body: JSON.stringify({ status, remarks }) })).data;
}

export async function approveApplication(id, data = {}) {
  return (await apiRequest(`/applications/${id}/approve/`, { method: "POST", body: JSON.stringify(data) })).data;
}

export async function rejectApplication(id, reason) {
  return (await apiRequest(`/applications/${id}/reject/`, { method: "POST", body: JSON.stringify({ reason }) })).data;
}