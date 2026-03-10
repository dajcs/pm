"use client";

import { useEffect, useState } from "react";
import type { ActivityEntry } from "@/lib/kanban";
import * as api from "@/lib/api";

interface ActivityFeedProps {
  boardId: number;
  onClose: () => void;
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export const ActivityFeed = ({ boardId, onClose }: ActivityFeedProps) => {
  const [entries, setEntries] = useState<ActivityEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getBoardActivity(boardId).then((data) => {
      setEntries(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [boardId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="relative w-full max-w-md rounded-2xl border border-[var(--stroke)] bg-white shadow-[var(--shadow)] p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-xl font-bold text-[var(--navy-dark)]">Activity</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-[var(--gray-text)] hover:text-[var(--navy-dark)] text-sm"
          >
            Close
          </button>
        </div>

        {loading ? (
          <p className="text-sm text-[var(--gray-text)]">Loading...</p>
        ) : entries.length === 0 ? (
          <p className="text-sm text-[var(--gray-text)]">No activity yet.</p>
        ) : (
          <ul className="flex flex-col gap-1.5 max-h-96 overflow-y-auto">
            {entries.map((e) => (
              <li key={e.id} className="flex items-start gap-3 rounded-xl px-3 py-2 hover:bg-[var(--surface)]">
                <div className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-[var(--primary-blue)]" />
                <div className="min-w-0 flex-1">
                  <span className="text-xs font-semibold text-[var(--navy-dark)]">{e.username}</span>
                  <span className="text-xs text-[var(--gray-text)]"> {e.action}</span>
                </div>
                <span className="shrink-0 text-[10px] text-[var(--gray-text)]">{formatRelative(e.created_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
