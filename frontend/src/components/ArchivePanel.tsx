"use client";

import { useEffect, useState } from "react";
import type { ArchivedCard } from "@/lib/kanban";
import * as api from "@/lib/api";

interface ArchivePanelProps {
  boardId?: number;
  onRestore: (cardId: string) => void;
  onClose: () => void;
}

export const ArchivePanel = ({ boardId, onRestore, onClose }: ArchivePanelProps) => {
  const [cards, setCards] = useState<ArchivedCard[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.listArchivedCards(boardId).then((data) => {
      setCards(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(load, [boardId]);

  const handleRestore = async (card: ArchivedCard) => {
    await api.restoreCard(card.id, boardId);
    setCards((prev) => prev.filter((c) => c.id !== card.id));
    onRestore(card.id);
  };

  const handleDelete = async (card: ArchivedCard) => {
    if (!confirm(`Permanently delete "${card.title}"?`)) return;
    await api.deleteCard(card.id, boardId);
    setCards((prev) => prev.filter((c) => c.id !== card.id));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="relative w-full max-w-lg rounded-2xl border border-[var(--stroke)] bg-white shadow-[var(--shadow)] p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-xl font-bold text-[var(--navy-dark)]">Archived Cards</h2>
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
        ) : cards.length === 0 ? (
          <p className="text-sm text-[var(--gray-text)]">No archived cards.</p>
        ) : (
          <ul className="flex flex-col gap-2 max-h-96 overflow-y-auto">
            {cards.map((card) => (
              <li
                key={card.id}
                className="flex items-start justify-between gap-3 rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3"
              >
                <div className="min-w-0 flex-1">
                  <p className="font-display text-sm font-semibold text-[var(--navy-dark)] truncate">{card.title}</p>
                  <p className="text-xs text-[var(--gray-text)] mt-0.5">
                    From: {card.column_title}
                    {card.due_date && ` · Due ${card.due_date}`}
                  </p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => handleRestore(card)}
                    className="text-xs font-semibold text-[var(--primary-blue)] hover:underline"
                  >
                    Restore
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(card)}
                    className="text-xs text-red-500 hover:underline"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
