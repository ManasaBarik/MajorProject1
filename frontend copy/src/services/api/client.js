const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");

let refreshing = null;

async function refreshAccessToken() {
  if (refreshing) return refreshing;
  const refresh = localStorage.getItem("civic_refresh_token");
  if (!refresh) return null;
  refreshing = fetch(`${API_BASE_URL}/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  }).then(async (res) => {
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error("refresh failed");
    const access = payload.data?.access || payload.access;
    if (access) sessionStorage.setItem("civic_access_token", access);
    const newRefresh = payload.data?.refresh || payload.refresh;
    if (newRefresh) localStorage.setItem("civic_refresh_token", newRefresh);
    return access;
  }).catch(() => null).finally(() => { refreshing = null; });
  return refreshing;
}

export async function apiRequest(path, options = {}, { retried = false } = {}) {
  const access = sessionStorage.getItem("civic_access_token");
  const headers = new Headers(options.headers || {});
  if (access) headers.set("Authorization", `Bearer ${access}`);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (response.status === 401 && !retried && access) {
    const newToken = await refreshAccessToken();
    if (newToken) return apiRequest(path, options, { retried: true });
  }
  if (response.status === 204) return null;
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.success === false) {
    const details = payload.error?.details;
    const detailMessage = details && typeof details === "object"
      ? Object.entries(details).map(([field, value]) => `${field}: ${Array.isArray(value) ? value.join(", ") : value}`).join(" ")
      : "";
    const error = new Error(detailMessage || payload.error?.message || "The request could not be completed.");
    error.code = payload.error?.code;
    error.details = payload.error?.details;
    error.status = response.status;
    throw error;
  }
  return payload;
}

export async function apiDownload(path, { retried = false } = {}) {
  const access = sessionStorage.getItem("civic_access_token");
  const headers = new Headers();
  if (access) headers.set("Authorization", `Bearer ${access}`);
  const response = await fetch(`${API_BASE_URL}${path}`, { headers });
  if (response.status === 401 && !retried && access) {
    const newToken = await refreshAccessToken();
    if (newToken) return apiDownload(path, { retried: true });
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error?.message || "The file could not be downloaded.");
  }
  return response.blob();
}

export { API_BASE_URL };