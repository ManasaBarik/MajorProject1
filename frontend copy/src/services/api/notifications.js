import { apiRequest } from "./client";

export async function listNotifications() {
  return (await apiRequest("/notifications/")).data;
}

export async function markNotificationRead(id) {
  return (await apiRequest(`/notifications/${id}/read/`, { method: "PATCH" })).data;
}

export async function markAllNotificationsRead() {
  return (await apiRequest("/notifications/read-all/", { method: "POST" })).data;
}