"use client";

import { useEffect, useState } from "react";
import * as api from "@/lib/api";

type Props = {
  cardId: string;
  boardId?: number;
};

export const CardSprintPanel = ({ cardId, boardId }: Props) => {
  const [cardSprints, setCardSprints] = useState<{ id: number; name: string; status: string }[]>([]);
  const [allSprints, setAllSprints] = useState<api.Sprint[]>([]);
  const [selectedSprintId, setSelectedSprintId] = useState("");

  const load = () => {
    if (!boardId) return;
    Promise.all([
      api.getCardSprints(cardId, boardId),
      api.listSprints(boardId),
    ]).then(([cs, all]) => {
      setCardSprints(cs);
      setAllSprints(all);
    }).catch(() => {});
  };

  useEffect(() => { load(); }, [cardId, boardId]);

  const handleAdd = async () => {
    if (!selectedSprintId || !boardId) return;
    await api.assignCardToSprint(cardId, parseInt(selectedSprintId), boardId).catch(() => {});
    setSelectedSprintId("");
    load();
  };

  const handleRemove = async (sprintId: number) => {
    if (!boardId) return;
    await api.removeCardFromSprint(cardId, sprintId, boardId).catch(() => {});
    load();
  };

  const unassigned = allSprints.filter((s) => !cardSprints.some((cs) => cs.id === s.id));

  return (
    <div className="space-y-2">
      {cardSprints.length > 0 && (
        <div className="space-y-1">
          {cardSprints.map((s) => (
            <div key={s.id} className="flex items-center justify-between rounded-lg border border-[var(--stroke)] bg-[var(--surface)] px-2 py-1">
              <span className="text-xs text-[var(--navy-dark)]">{s.name}</span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[var(--gray-text)]">{s.status}</span>
                <button
                  onClick={() => handleRemove(s.id)}
                  className="text-[10px] text-[var(--gray-text)] hover:text-red-500"
                >
                  remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      {unassigned.length > 0 && (
        <div className="flex gap-1">
          <select
            value={selectedSprintId}
            onChange={(e) => setSelectedSprintId(e.target.value)}
            className="flex-1 rounded-lg border border-[var(--stroke)] px-2 py-1 text-xs text-[var(--navy-dark)] bg-white outline-none focus:border-[var(--primary-blue)]"
          >
            <option value="">-- add to sprint --</option>
            {unassigned.map((s) => (
              <option key={s.id} value={s.id}>{s.name} ({s.status})</option>
            ))}
          </select>
          <button
            onClick={handleAdd}
            disabled={!selectedSprintId}
            className="rounded-lg bg-[var(--primary-blue)] px-3 py-1 text-xs font-semibold text-white disabled:opacity-40 hover:opacity-90"
          >
            +
          </button>
        </div>
      )}
      {allSprints.length === 0 && (
        <p className="text-xs text-[var(--gray-text)]">No sprints on this board yet.</p>
      )}
    </div>
  );
};
