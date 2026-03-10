import type { ActivityEntry, ArchivedCard, BoardData, ChecklistItem, Comment } from "./kanban";

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
  boardId?: number,
  due_date?: string | null,
  priority?: string
): Promise<{ id: string; title: string; details: string; due_date?: string | null; priority?: string }> {
  return request(`/api/board/cards${boardParam(boardId)}`, {
    method: "POST",
    body: JSON.stringify({ column_id: columnId, title, details, due_date, priority }),
  });
}

export async function deleteCard(cardId: string, boardId?: number): Promise<void> {
  await request(`/api/board/cards/${cardId}${boardParam(boardId)}`, { method: "DELETE" });
}

export async function updateCard(
  cardId: string,
  fields: { title?: string; details?: string; due_date?: string | null; priority?: string; labels?: string[]; assigned_to?: string | null },
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

export async function setColumnWipLimit(
  columnId: string,
  wipLimit: number | null,
  boardId?: number
): Promise<void> {
  await request(`/api/board/columns/${columnId}/wip-limit${boardParam(boardId)}`, {
    method: "PUT",
    body: JSON.stringify({ wip_limit: wipLimit }),
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

export interface BoardStats {
  total_cards: number;
  cards_by_column: Record<string, number>;
  overdue_count: number;
  cards_by_priority: Record<string, number>;
  due_soon_count: number;
  assigned_count: number;
  unassigned_count: number;
}

export async function getBoardStats(boardId: number): Promise<BoardStats> {
  return request<BoardStats>(`/api/boards/${boardId}/stats`);
}

export async function updateBoardDescription(boardId: number, description: string): Promise<void> {
  await request(`/api/boards/${boardId}/description`, {
    method: "PATCH",
    body: JSON.stringify({ description }),
  });
}

// --- Checklist ---

export async function getChecklist(cardId: string, boardId?: number): Promise<ChecklistItem[]> {
  return request<ChecklistItem[]>(`/api/board/cards/${cardId}/checklist${boardParam(boardId)}`);
}

export async function addChecklistItem(
  cardId: string, text: string, boardId?: number
): Promise<ChecklistItem> {
  return request<ChecklistItem>(`/api/board/cards/${cardId}/checklist${boardParam(boardId)}`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export async function updateChecklistItem(
  cardId: string, itemId: number,
  fields: { text?: string; checked?: boolean },
  boardId?: number
): Promise<void> {
  await request(`/api/board/cards/${cardId}/checklist/${itemId}${boardParam(boardId)}`, {
    method: "PATCH",
    body: JSON.stringify(fields),
  });
}

export async function deleteChecklistItem(
  cardId: string, itemId: number, boardId?: number
): Promise<void> {
  await request(`/api/board/cards/${cardId}/checklist/${itemId}${boardParam(boardId)}`, {
    method: "DELETE",
  });
}

// --- Search & Members ---

export async function searchCards(query: string, boardId?: number): Promise<string[]> {
  const bp = boardId ? `&board_id=${boardId}` : "";
  return request<string[]>(`/api/board/search?q=${encodeURIComponent(query)}${bp}`);
}

export async function getBoardMembers(boardId: number): Promise<string[]> {
  return request<string[]>(`/api/boards/${boardId}/members`);
}

// --- Export ---

export async function exportBoard(boardId: number): Promise<unknown> {
  return request(`/api/boards/${boardId}/export`);
}

export async function logBoardActivity(boardId: number, action: string): Promise<void> {
  await request(`/api/boards/${boardId}/activity`, {
    method: "POST",
    body: JSON.stringify({ action }),
  });
}

// --- Archive ---

export async function archiveCard(cardId: string, boardId?: number): Promise<void> {
  await request(`/api/board/cards/${cardId}/archive${boardParam(boardId)}`, { method: "POST" });
}

export async function archiveColumnCards(columnId: string, boardId?: number): Promise<{ archived_count: number }> {
  return request(`/api/board/columns/${columnId}/archive-all${boardParam(boardId)}`, { method: "POST" });
}

export async function restoreCard(cardId: string, boardId?: number): Promise<void> {
  await request(`/api/board/cards/${cardId}/restore${boardParam(boardId)}`, { method: "POST" });
}

export async function listArchivedCards(boardId?: number): Promise<ArchivedCard[]> {
  return request<ArchivedCard[]>(`/api/board/archived-cards${boardParam(boardId)}`);
}

// --- Comments ---

export async function getComments(cardId: string, boardId?: number): Promise<Comment[]> {
  return request<Comment[]>(`/api/board/cards/${cardId}/comments${boardParam(boardId)}`);
}

export async function addComment(cardId: string, text: string, boardId?: number): Promise<Comment> {
  return request<Comment>(`/api/board/cards/${cardId}/comments${boardParam(boardId)}`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export async function deleteComment(cardId: string, commentId: number, boardId?: number): Promise<void> {
  await request(`/api/board/cards/${cardId}/comments/${commentId}${boardParam(boardId)}`, {
    method: "DELETE",
  });
}

// --- Activity ---

export async function getBoardActivity(boardId: number): Promise<ActivityEntry[]> {
  return request<ActivityEntry[]>(`/api/boards/${boardId}/activity`);
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
