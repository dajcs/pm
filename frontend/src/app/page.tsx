"use client";

import { useCallback, useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { ChatSidebar } from "@/components/ChatSidebar";
import { LoginPage } from "@/components/LoginPage";
import { RegisterPage } from "@/components/RegisterPage";
import { setAuthErrorHandler, listBoards, createBoardApi, renameBoardApi, deleteBoardApi } from "@/lib/api";
import type { Board } from "@/lib/api";
import type { BoardData } from "@/lib/kanban";

type AuthScreen = "login" | "register";

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);
  const [authScreen, setAuthScreen] = useState<AuthScreen>("login");
  const [pendingBoard, setPendingBoard] = useState<BoardData | null>(null);
  const [boards, setBoards] = useState<Board[]>([]);
  const [currentBoardId, setCurrentBoardId] = useState<number | undefined>(undefined);

  const handleLogout = useCallback(() => {
    localStorage.removeItem("token");
    setToken(null);
    setBoards([]);
    setCurrentBoardId(undefined);
  }, []);

  // Register the global auth error handler
  useEffect(() => {
    setAuthErrorHandler(handleLogout);
  }, [handleLogout]);

  useEffect(() => {
    const stored = localStorage.getItem("token");
    if (!stored) {
      setChecking(false);
      return;
    }
    fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${stored}` },
    })
      .then((res) => {
        if (res.ok) setToken(stored);
        else localStorage.removeItem("token");
      })
      .catch(() => localStorage.removeItem("token"))
      .finally(() => setChecking(false));
  }, []);

  // Load boards after login
  useEffect(() => {
    if (!token) return;
    // First fetch the default board to trigger lazy creation, then list
    fetch("/api/board", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(() => listBoards())
      .then((data) => {
        setBoards(data);
        if (data.length > 0 && currentBoardId === undefined) {
          setCurrentBoardId(data[0].id);
        }
      })
      .catch(() => {/* non-fatal */});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const handleLogin = useCallback((jwt: string) => {
    localStorage.setItem("token", jwt);
    setToken(jwt);
  }, []);

  const handleBoardUpdated = useCallback((board: BoardData) => {
    setPendingBoard(board);
  }, []);

  const handlePendingBoardApplied = useCallback(() => {
    setPendingBoard(null);
  }, []);

  const handleBoardSelect = useCallback((boardId: number) => {
    setCurrentBoardId(boardId);
    setPendingBoard(null);
  }, []);

  const handleBoardCreate = useCallback(async (name: string) => {
    try {
      const board = await createBoardApi(name);
      setBoards((prev) => [...prev, board]);
      setCurrentBoardId(board.id);
      setPendingBoard(null);
    } catch {/* non-fatal */}
  }, []);

  const handleBoardRename = useCallback(async (boardId: number, name: string) => {
    try {
      await renameBoardApi(boardId, name);
      setBoards((prev) =>
        prev.map((b) => (b.id === boardId ? { ...b, name } : b))
      );
    } catch {/* non-fatal */}
  }, []);

  const handleBoardDelete = useCallback(async (boardId: number) => {
    try {
      await deleteBoardApi(boardId);
      setBoards((prev) => {
        const next = prev.filter((b) => b.id !== boardId);
        if (currentBoardId === boardId && next.length > 0) {
          setCurrentBoardId(next[0].id);
        }
        return next;
      });
      setPendingBoard(null);
    } catch {/* non-fatal */}
  }, [currentBoardId]);

  if (checking) return null;

  if (!token) {
    if (authScreen === "register") {
      return (
        <RegisterPage
          onRegister={handleLogin}
          onBackToLogin={() => setAuthScreen("login")}
        />
      );
    }
    return (
      <LoginPage
        onLogin={handleLogin}
        onRegister={() => setAuthScreen("register")}
      />
    );
  }

  return (
    <div className="flex min-h-screen">
      <div className="min-w-0 flex-1 overflow-auto">
        <KanbanBoard
          onLogout={handleLogout}
          pendingBoard={pendingBoard}
          onPendingBoardApplied={handlePendingBoardApplied}
          boardId={currentBoardId}
          boards={boards}
          onBoardSelect={handleBoardSelect}
          onBoardCreate={handleBoardCreate}
          onBoardRename={handleBoardRename}
          onBoardDelete={handleBoardDelete}
        />
      </div>
      <div className="sticky top-0 h-screen p-4 pl-0">
        <ChatSidebar
          onBoardUpdated={handleBoardUpdated}
          boardId={currentBoardId}
        />
      </div>
    </div>
  );
}
