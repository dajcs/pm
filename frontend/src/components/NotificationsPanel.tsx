"use client";

import { useEffect, useState } from "react";
import type { AppNotification } from "@/lib/api";
import * as api from "@/lib/api";

type Props = {
  onClose: () => void;
  onNavigateBoard?: (boardId: number) => void;
};

const TYPE_LABEL: Record<string, string> = {
  assignment: "assigned",
  mention: "mentioned",
};

export const NotificationsPanel = ({ onClose, onNavigateBoard }: Props) => {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    api.getNotifications().then(setNotifications).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleMarkAllRead = async () => {
    await api.markNotificationsRead();
    load();
  };

  const handleMarkRead = async (id: number) => {
    await api.markNotificationsRead([id]);
    setNotifications((prev) => prev.map((n) => n.id === id ? { ...n, read: true } : n));
  };

  const handleDelete = async (id: number) => {
    await api.deleteNotification(id).catch(() => {});
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="relative w-full max-w-md max-h-[80vh] overflow-y-auto rounded-2xl border border-[var(--stroke)] bg-white shadow-[var(--shadow)] p-6">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-[var(--gray-text)] hover:text-[var(--navy-dark)] text-lg leading-none"
        >
          x
        </button>
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-display text-xl font-bold text-[var(--navy-dark)]">
            Notifications
            {unreadCount > 0 && (
              <span className="ml-2 rounded-full bg-[var(--primary-blue)] px-2 py-0.5 text-xs font-semibold text-white">
                {unreadCount}
              </span>
            )}
          </h2>
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="text-xs text-[var(--primary-blue)] hover:underline"
            >
              mark all read
            </button>
          )}
        </div>

        {loading && (
          <p className="text-sm text-center text-[var(--gray-text)] py-8">Loading...</p>
        )}

        {!loading && notifications.length === 0 && (
          <p className="text-sm text-center text-[var(--gray-text)] py-8">No notifications.</p>
        )}

        <div className="space-y-2">
          {notifications.map((n) => (
            <div
              key={n.id}
              className={`rounded-xl border px-4 py-3 flex items-start gap-3 transition-colors ${
                n.read
                  ? "border-[var(--stroke)] bg-[var(--surface)]"
                  : "border-[var(--primary-blue)] bg-blue-50"
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--gray-text)]">
                    {TYPE_LABEL[n.type] ?? n.type}
                  </span>
                  {!n.read && (
                    <span className="h-1.5 w-1.5 rounded-full bg-[var(--primary-blue)] shrink-0" />
                  )}
                </div>
                <p className="text-sm text-[var(--navy-dark)]">{n.message}</p>
                <p className="text-[10px] text-[var(--gray-text)] mt-0.5">
                  {new Date(n.created_at).toLocaleString()}
                </p>
              </div>
              <div className="flex flex-col items-end gap-1 shrink-0">
                {n.board_id && onNavigateBoard && (
                  <button
                    onClick={() => { onNavigateBoard(n.board_id!); onClose(); }}
                    className="text-[10px] text-[var(--primary-blue)] hover:underline"
                  >
                    go
                  </button>
                )}
                {!n.read && (
                  <button
                    onClick={() => handleMarkRead(n.id)}
                    className="text-[10px] text-[var(--gray-text)] hover:text-[var(--navy-dark)]"
                  >
                    read
                  </button>
                )}
                <button
                  onClick={() => handleDelete(n.id)}
                  className="text-[10px] text-[var(--gray-text)] hover:text-red-500"
                >
                  delete
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
