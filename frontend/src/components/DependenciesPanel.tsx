"use client";

import { useEffect, useState } from "react";
import type { CardDependencies } from "@/lib/api";
import * as api from "@/lib/api";

type DependenciesPanelProps = {
  cardId: string;
  boardId?: number;
  allCardTitles?: Record<string, string>; // id -> title for autocomplete
};

export const DependenciesPanel = ({ cardId, boardId, allCardTitles }: DependenciesPanelProps) => {
  const [deps, setDeps] = useState<CardDependencies>({ blocked_by: [], blocking: [] });
  const [addingId, setAddingId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loadDeps = () => {
    api.getCardDependencies(cardId, boardId)
      .then(setDeps)
      .catch(() => {});
  };

  useEffect(() => { loadDeps(); }, [cardId, boardId]);

  const handleAdd = async () => {
    const id = addingId.trim();
    if (!id) return;
    setError(null);
    try {
      await api.addCardDependency(cardId, id, boardId);
      setAddingId("");
      loadDeps();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to add dependency");
    }
  };

  const handleRemove = async (dependsOnId: string) => {
    await api.removeCardDependency(cardId, dependsOnId, boardId).catch(() => {});
    loadDeps();
  };

  return (
    <div className="space-y-2">
      {/* Blocked by */}
      {deps.blocked_by.length > 0 && (
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.15em] text-red-500 mb-1">
            Blocked by
          </div>
          {deps.blocked_by.map((dep) => (
            <div key={dep.id} className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50 px-2 py-1 mb-1">
              <span className="text-xs text-[var(--navy-dark)] truncate">{dep.title}</span>
              <button
                onClick={() => handleRemove(dep.id)}
                className="text-[10px] text-red-400 hover:text-red-600 ml-2 shrink-0"
              >
                remove
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Blocking */}
      {deps.blocking.length > 0 && (
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.15em] text-orange-500 mb-1">
            Blocking
          </div>
          {deps.blocking.map((dep) => (
            <div key={dep.id} className="flex items-center rounded-lg border border-orange-200 bg-orange-50 px-2 py-1 mb-1">
              <span className="text-xs text-[var(--navy-dark)] truncate">{dep.title}</span>
            </div>
          ))}
        </div>
      )}

      {/* Add dependency */}
      <div className="flex gap-1">
        {allCardTitles ? (
          <select
            value={addingId}
            onChange={(e) => setAddingId(e.target.value)}
            className="flex-1 rounded-lg border border-[var(--stroke)] px-2 py-1 text-xs text-[var(--navy-dark)] bg-white outline-none focus:border-[var(--primary-blue)]"
          >
            <option value="">-- select card --</option>
            {Object.entries(allCardTitles)
              .filter(([id]) => id !== cardId && !deps.blocked_by.some((d) => d.id === id))
              .map(([id, title]) => (
                <option key={id} value={id}>{title}</option>
              ))}
          </select>
        ) : (
          <input
            type="text"
            placeholder="card ID"
            value={addingId}
            onChange={(e) => setAddingId(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleAdd(); }}
            className="flex-1 rounded-lg border border-[var(--stroke)] px-2 py-1 text-xs text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          />
        )}
        <button
          onClick={handleAdd}
          disabled={!addingId}
          className="rounded-lg bg-[var(--primary-blue)] px-3 py-1 text-xs font-semibold text-white disabled:opacity-40 hover:opacity-90"
        >
          +
        </button>
      </div>
      {error && <p className="text-[10px] text-red-500">{error}</p>}
    </div>
  );
};
