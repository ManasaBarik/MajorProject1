import { apiRequest } from "./client";

export async function login(email, password) {
  return (await apiRequest("/auth/login/", { method: "POST", body: JSON.stringify({ email, password }) })).data;
}

export async function register(data) {
  return (await apiRequest("/auth/register/", { method: "POST", body: JSON.stringify(data) })).data;
}

export async function getMe() {
  return (await apiRequest("/auth/me/")).data;
}

export async function updateMe(data) {
  return (await apiRequest("/users/me/", { method: "PATCH", body: JSON.stringify(data) })).data;
}

export async function logout() {
  const refresh = localStorage.getItem("civic_refresh_token");
  try { await apiRequest("/auth/logout/", { method: "POST", body: JSON.stringify({ refresh }) }); } catch {}
  return null;
}

export async function passwordReset(email) {
  return (await apiRequest("/auth/password-reset/", { method: "POST", body: JSON.stringify({ email }) })).data;
}

export async function passwordResetConfirm(resetToken, newPassword) {
  return (await apiRequest("/auth/password-reset/confirm/", { method: "POST", body: JSON.stringify({ reset_token: resetToken, new_password: newPassword }) })).data;
}