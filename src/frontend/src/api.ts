const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export type ChatResponse = {
  conversation_id: string;
  assistant_message: string;
  span_id: string;
  root_span_id?: string | null;
};

export async function sendChat(
  conversationId: string,
  message: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, message }),
  });
  if (!res.ok) {
    throw new Error("Chat request failed");
  }
  return res.json();
}

export async function sendFeedback(
  spanId: string,
  rating?: "up" | "down",
  comment?: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ span_id: spanId, rating, comment }),
  });
  if (!res.ok) {
    throw new Error("Feedback request failed");
  }
}

export async function uploadDocument(
  conversationId: string,
  file: File
): Promise<void> {
  const form = new FormData();
  form.append("conversation_id", conversationId);
  form.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    throw new Error("Upload failed");
  }
}
