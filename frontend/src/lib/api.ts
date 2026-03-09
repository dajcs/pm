import type { BoardData } from "./kanban";

export interface Board {
  id: number;
  name: string;
  created_at: string;
}

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
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `API error: ${res.status}`);
  }

  return res.json();
}

function boardParam(boardId?: number): string {
  return boardId ? `?board_id=${boardId}` : "";
}

export async function fetchBoard(boardId?: number): Promise<BoardData> {
  return request<BoardData>(`/api/board${boardParam(boardId)}`);
}

export async function saveBoard(data: BoardData, boardId?: number): Promise<BoardData> {
  return request<BoardData>(`/api/board${boardParam(boardId)}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function createCard(
  columnId: string,
  title: string,
  details: string,
  boardId?: number
): Promise<{ id: string; title: string; details: string }> {
  return request(`/api/board/cards${boardParam(boardId)}`, {
    method: "POST",
    body: JSON.stringify({ column_id: columnId, title, details }),
  });
}

export async function deleteCard(cardId: string, boardId?: number): Promise<void> {
  await request(`/api/board/cards/${cardId}${boardParam(boardId)}`, { method: "DELETE" });
}

export async function updateCard(
  cardId: string,
  fields: { title?: string; details?: string },
  boardId?: number
): Promise<void> {
  await request(`/api/board/cards/${cardId}${boardParam(boardId)}`, {
    method: "PATCH",
    body: JSON.stringify(fields),
  });
}

export async function renameColumn(
  columnId: string,
  title: string,
  boardId?: number
): Promise<void> {
  await request(`/api/board/columns/${columnId}${boardParam(boardId)}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
}

export async function addColumn(
  title: string,
  boardId?: number
): Promise<{ id: string; title: string }> {
  return request(`/api/board/columns${boardParam(boardId)}`, {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

export async function deleteColumn(columnId: string, boardId?: number): Promise<void> {
  await request(`/api/board/columns/${columnId}${boardParam(boardId)}`, { method: "DELETE" });
}

export async function saveColumnsOrder(data: BoardData, boardId?: number): Promise<BoardData> {
  return request<BoardData>(`/api/board${boardParam(boardId)}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// --- Boards ---

export async function listBoards(): Promise<Board[]> {
  return request<Board[]>("/api/boards");
}

export async function createBoardApi(name: string): Promise<Board> {
  return request<Board>("/api/boards", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function renameBoardApi(id: number, name: string): Promise<void> {
  await request(`/api/boards/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export async function deleteBoardApi(id: number): Promise<void> {
  await request(`/api/boards/${id}`, { method: "DELETE" });
}

// --- Auth ---

export async function register(username: string, password: string): Promise<{ token: string }> {
  return request<{ token: string }>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function changePassword(
  currentPassword: string,
  newPassword: string
): Promise<void> {
  await request("/api/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}

export interface ChatResponse {
  message: string;
  board_update: BoardData | null;
}

export async function sendChatMessage(
  message: string,
  history: { role: string; content: string }[],
  boardId?: number
): Promise<ChatResponse> {
  return request<ChatResponse>(`/api/ai/chat${boardParam(boardId)}`, {
    method: "POST",
    body: JSON.stringify({ message, history }),
  });
}
