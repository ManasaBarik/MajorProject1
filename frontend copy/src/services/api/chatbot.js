import { apiRequest } from "./client";

export async function sendChat(message, language = "en", context = "CITIZEN") {
  return (await apiRequest("/chatbot/chat/", { method: "POST", body: JSON.stringify({ message, language, context }) })).data;
}

export async function listConversations() {
  return (await apiRequest("/chatbot/conversations/")).data;
}

export async function getConversation(id) {
  return (await apiRequest(`/chatbot/conversations/${id}/`)).data;
}