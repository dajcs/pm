import type { BoardData } from "./kanban";

let onAuthError: (() => void) | null = null;

export function setAuthErrorHandler(handler: () => void) {
  onAuthError = handler;
}

function getToken(): string {
  return localStorage.getItem("token") ?? "";
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
      ...options.headers,
    },
  });

  if (res.status === 401) {
    localStorage.removeItem("token");
    onAuthError?.();
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  return res.json();
}

export async function fetchBoard(): Promise<BoardData> {
  return request<BoardData>("/api/board");
}

export async function saveBoard(data: BoardData): Promise<BoardData> {
  return request<BoardData>("/api/board", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function createCard(
  columnId: string,
  title: string,
  details: string
): Promise<{ id: string; title: string; details: string }> {
  return request("/api/board/cards", {
    method: "POST",
    body: JSON.stringify({ column_id: columnId, title, details }),
  });
}

export async function deleteCard(cardId: string): Promise<void> {
  await request(`/api/board/cards/${cardId}`, { method: "DELETE" });
}

export async function updateCard(
  cardId: string,
  fields: { title?: string; details?: string }
): Promise<void> {
  await request(`/api/board/cards/${cardId}`, {
    method: "PATCH",
    body: JSON.stringify(fields),
  });
}

export async function renameColumn(
  columnId: string,
  title: string
): Promise<void> {
  await request(`/api/board/columns/${columnId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
}

export async function saveColumnsOrder(data: BoardData): Promise<BoardData> {
  return request<BoardData>("/api/board/columns/order", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export interface ChatResponse {
  message: string;
  board_update: BoardData | null;
}

export async function sendChatMessage(
  message: string,
  history: { role: string; content: string }[]
): Promise<ChatResponse> {
  return request<ChatResponse>("/api/ai/chat", {
    method: "POST",
    body: JSON.stringify({ message, history }),
  });
}
