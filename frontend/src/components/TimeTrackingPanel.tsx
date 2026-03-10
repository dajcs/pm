"use client";

import { useEffect, useState } from "react";
import type { TimeEntry } from "@/lib/api";
import * as api from "@/lib/api";

type Props = {
  cardId: string;
  boardId?: number;
  onTotalChange?: (total: number) => void;
};

export const TimeTrackingPanel = ({ cardId, boardId, onTotalChange }: Props) => {
  const [entries, setEntries] = useState<TimeEntry[]>([]);
  const [hours, setHours] = useState("");
  const [description, setDescription] = useState("");
  const [date, setDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  const load = () => {
    api.getTimeEntries(cardId, boardId).then((list) => {
      setEntries(list);
      const total = list.reduce((s, e) => s + e.hours, 0);
      onTotalChange?.(Math.round(total * 100) / 100);
    }).catch(() => {});
  };

  useEffect(() => { load(); }, [cardId, boardId]);

  const handleAdd = async () => {
    const h = parseFloat(hours);
    if (!hours || isNaN(h) || h <= 0 || h > 24) {
      setError("Hours must be between 0 and 24");
      return;
    }
    if (!date) { setError("Date is required"); return; }
    setError(null);
    setAdding(true);
    try {
      await api.addTimeEntry(cardId, h, description.trim(), date, boardId);
      setHours("");
      setDescription("");
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to add entry");
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (entryId: number) => {
    await api.deleteTimeEntry(cardId, entryId, boardId).catch(() => {});
    load();
  };

  const total = entries.reduce((s, e) => s + e.hours, 0);

  return (
    <div className="space-y-2">
      {entries.length > 0 && (
        <div className="space-y-1">
          {entries.map((e) => (
            <div
              key={e.id}
              className="flex items-center justify-between rounded-lg border border-[var(--stroke)] bg-[var(--surface)] px-3 py-1.5 gap-2"
            >
              <div className="min-w-0">
                <span className="text-xs font-semibold text-[var(--navy-dark)]">{e.hours}h</span>
                {e.description && (
                  <span className="text-xs text-[var(--gray-text)] ml-2 truncate">{e.description}</span>
                )}
                <span className="text-[10px] text-[var(--gray-text)] ml-2">{e.date} · {e.username}</span>
              </div>
              <button
                onClick={() => handleDelete(e.id)}
                className="text-[10px] text-[var(--gray-text)] hover:text-red-500 shrink-0"
              >
                remove
              </button>
            </div>
          ))}
          <div className="text-right text-xs font-semibold text-[var(--navy-dark)] pr-1">
            Total: {Math.round(total * 100) / 100}h
          </div>
        </div>
      )}

      {/* Add entry form */}
      <div className="flex gap-1 flex-wrap">
        <input
          type="number"
          min="0.1"
          max="24"
          step="0.25"
          placeholder="Hours"
          value={hours}
          onChange={(e) => setHours(e.target.value)}
          className="w-20 rounded-lg border border-[var(--stroke)] px-2 py-1 text-xs text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
        />
        <input
          type="text"
          placeholder="Description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") handleAdd(); }}
          className="flex-1 min-w-0 rounded-lg border border-[var(--stroke)] px-2 py-1 text-xs text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
        />
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="rounded-lg border border-[var(--stroke)] px-2 py-1 text-xs text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
        />
        <button
          onClick={handleAdd}
          disabled={adding || !hours}
          className="rounded-lg bg-[var(--primary-blue)] px-3 py-1 text-xs font-semibold text-white disabled:opacity-40 hover:opacity-90"
        >
          log
        </button>
      </div>
      {error && <p className="text-[10px] text-red-500">{error}</p>}
    </div>
  );
};
