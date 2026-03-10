"use client";

import { useEffect, useState } from "react";
import type { BoardMember } from "@/lib/api";
import * as api from "@/lib/api";

type BoardSharePanelProps = {
  boardId: number;
  onClose: () => void;
  onMembersChanged?: () => void;
};

export const BoardSharePanel = ({ boardId, onClose, onMembersChanged }: BoardSharePanelProps) => {
  const [members, setMembers] = useState<BoardMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteUsername, setInviteUsername] = useState("");
  const [inviting, setInviting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadMembers = () => {
    setLoading(true);
    api.getBoardMembersWithRoles(boardId)
      .then(setMembers)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadMembers();
  }, [boardId]);

  const handleInvite = async () => {
    const username = inviteUsername.trim();
    if (!username) return;
    setInviting(true);
    setError(null);
    try {
      await api.inviteBoardMember(boardId, username);
      setInviteUsername("");
      loadMembers();
      onMembersChanged?.();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to invite");
    } finally {
      setInviting(false);
    }
  };

  const handleRemove = async (username: string) => {
    if (!confirm(`Remove ${username} from this board?`)) return;
    try {
      await api.removeBoardMember(boardId, username);
      loadMembers();
      onMembersChanged?.();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to remove");
    }
  };

  const owner = members.find((m) => m.role === "owner");
  const collaborators = members.filter((m) => m.role !== "owner");

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="relative w-full max-w-md rounded-2xl border border-[var(--stroke)] bg-white shadow-[var(--shadow)] p-6">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-[var(--gray-text)] hover:text-[var(--navy-dark)] text-lg leading-none"
          aria-label="Close"
        >
          x
        </button>
        <h2 className="font-display text-xl font-bold text-[var(--navy-dark)] mb-5">
          Share Board
        </h2>

        {/* Invite form */}
        <div className="mb-5">
          <label className="block text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] mb-2">
            Invite by username
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="username"
              value={inviteUsername}
              onChange={(e) => setInviteUsername(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleInvite(); }}
              className="flex-1 rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
            />
            <button
              onClick={handleInvite}
              disabled={inviting || !inviteUsername.trim()}
              className="rounded-xl bg-[var(--primary-blue)] px-4 py-2 text-xs font-semibold text-white disabled:opacity-50 hover:opacity-90 transition-opacity"
            >
              {inviting ? "..." : "Invite"}
            </button>
          </div>
          {error && (
            <p className="mt-1.5 text-xs text-red-500">{error}</p>
          )}
        </div>

        {/* Members list */}
        {loading ? (
          <p className="text-sm text-[var(--gray-text)] text-center py-4">Loading...</p>
        ) : (
          <div className="space-y-2">
            <div className="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] mb-3">
              Members ({members.length})
            </div>
            {owner && (
              <div className="flex items-center justify-between rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2">
                <div>
                  <span className="text-sm font-semibold text-[var(--navy-dark)]">@{owner.username}</span>
                  <span className="ml-2 rounded-full bg-[var(--primary-blue)] px-2 py-0.5 text-[10px] font-semibold text-white uppercase tracking-wide">owner</span>
                </div>
              </div>
            )}
            {collaborators.map((m) => (
              <div key={m.username} className="flex items-center justify-between rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2">
                <div>
                  <span className="text-sm font-semibold text-[var(--navy-dark)]">@{m.username}</span>
                  <span className="ml-2 rounded-full bg-[var(--secondary-purple)] px-2 py-0.5 text-[10px] font-semibold text-white uppercase tracking-wide">member</span>
                </div>
                {owner && (
                  <button
                    onClick={() => handleRemove(m.username)}
                    className="text-xs text-[var(--gray-text)] hover:text-red-500 transition-colors"
                    title={`Remove ${m.username}`}
                  >
                    remove
                  </button>
                )}
              </div>
            ))}
            {collaborators.length === 0 && (
              <p className="text-xs text-[var(--gray-text)] text-center py-3">
                No collaborators yet. Invite someone to collaborate!
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
