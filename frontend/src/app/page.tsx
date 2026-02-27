"use client";

import { useCallback, useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { LoginPage } from "@/components/LoginPage";
import { setAuthErrorHandler } from "@/lib/api";

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);

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

  if (checking) return null;

  if (!token) return <LoginPage onLogin={handleLogin} />;

  return <KanbanBoard onLogout={handleLogout} />;
}
