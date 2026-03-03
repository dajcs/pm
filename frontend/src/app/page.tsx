"use client";

import { useCallback, useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { ChatSidebar } from "@/components/ChatSidebar";
import { LoginPage } from "@/components/LoginPage";
import { setAuthErrorHandler } from "@/lib/api";
import type { BoardData } from "@/lib/kanban";

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);
  const [pendingBoard, setPendingBoard] = useState<BoardData | null>(null);

  const handleLogout = useCallback(() => {
    localStorage.removeItem("token");
    setToken(null);
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

  if (checking) return null;

  if (!token) return <LoginPage onLogin={handleLogin} />;

  return (
    <div className="flex min-h-screen">
      <div className="flex-1 overflow-auto">
        <KanbanBoard
          onLogout={handleLogout}
          pendingBoard={pendingBoard}
          onPendingBoardApplied={handlePendingBoardApplied}
        />
      </div>
      <div className="sticky top-0 h-screen p-4 pl-0">
        <ChatSidebar onBoardUpdated={handleBoardUpdated} />
      </div>
    </div>
  );
}
