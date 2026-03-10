"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import type { Sprint } from "@/lib/api";
import * as api from "@/lib/api";

type Props = {
  boardId: number;
  onClose: () => void;
};

const STATUS_STYLE: Record<string, string> = {
  planned: "bg-gray-100 text-gray-600 border-gray-200",
  active: "bg-blue-100 text-blue-700 border-blue-200",
  completed: "bg-green-100 text-green-700 border-green-200",
};

const STATUS_OPTIONS = ["planned", "active", "completed"];

export const SprintPanel = ({ boardId, onClose }: Props) => {
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [newName, setNewName] = useState("");
  const [newGoal, setNewGoal] = useState("");
  const [newStart, setNewStart] = useState("");
  const [newEnd, setNewEnd] = useState("");
  const [creating, setCreating] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedCards, setExpandedCards] = useState<api.SprintCard[]>([]);

  const load = () => {
    api.listSprints(boardId).then(setSprints).catch(() => {});
  };

  useEffect(() => { load(); }, [boardId]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await api.createSprint(boardId, newName.trim(), newGoal.trim(), newStart || null, newEnd || null);
      setNewName(""); setNewGoal(""); setNewStart(""); setNewEnd("");
      load();
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: number) => {
    await api.deleteSprint(boardId, id).catch(() => {});
    if (expandedId === id) setExpandedId(null);
    load();
  };

  const handleStatusChange = async (id: number, status: string) => {
    await api.updateSprint(boardId, id, { status }).catch(() => {});
    load();
  };

  const handleExpand = async (id: number) => {
    if (expandedId === id) { setExpandedId(null); return; }
    const detail = await api.getSprint(boardId, id).catch(() => null);
    if (detail) { setExpandedCards(detail.cards); setExpandedId(id); }
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="relative w-full max-w-xl max-h-[85vh] overflow-y-auto rounded-2xl border border-[var(--stroke)] bg-white shadow-[var(--shadow)] p-6">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-[var(--gray-text)] hover:text-[var(--navy-dark)] text-lg leading-none"
        >
          x
        </button>
        <h2 className="font-display text-xl font-bold text-[var(--navy-dark)] mb-5">Sprints</h2>

        {/* Create sprint form */}
        <div className="rounded-xl border border-[var(--stroke)] bg-[var(--surface)] p-4 mb-5 space-y-2">
          <div className="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] mb-1">New Sprint</div>
          <input
            type="text"
            placeholder="Sprint name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleCreate(); }}
            className="w-full rounded-lg border border-[var(--stroke)] px-3 py-1.5 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          />
          <input
            type="text"
            placeholder="Goal (optional)"
            value={newGoal}
            onChange={(e) => setNewGoal(e.target.value)}
            className="w-full rounded-lg border border-[var(--stroke)] px-3 py-1.5 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          />
          <div className="flex gap-2">
            <div className="flex items-center gap-1 flex-1">
              <span className="text-xs text-[var(--gray-text)]">Start</span>
              <input type="date" value={newStart} onChange={(e) => setNewStart(e.target.value)}
                className="flex-1 rounded-lg border border-[var(--stroke)] px-2 py-1 text-xs text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]" />
            </div>
            <div className="flex items-center gap-1 flex-1">
              <span className="text-xs text-[var(--gray-text)]">End</span>
              <input type="date" value={newEnd} onChange={(e) => setNewEnd(e.target.value)}
                className="flex-1 rounded-lg border border-[var(--stroke)] px-2 py-1 text-xs text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]" />
            </div>
          </div>
          <button
            onClick={handleCreate}
            disabled={creating || !newName.trim()}
            className="w-full rounded-lg bg-[var(--primary-blue)] py-1.5 text-sm font-semibold text-white disabled:opacity-40 hover:opacity-90"
          >
            Create Sprint
          </button>
        </div>

        {/* Sprint list */}
        {sprints.length === 0 && (
          <p className="text-sm text-center text-[var(--gray-text)] py-4">No sprints yet.</p>
        )}
        <div className="space-y-3">
          {sprints.map((sprint) => {
            const progress = sprint.total_cards ? Math.round(((sprint.done_cards ?? 0) / sprint.total_cards) * 100) : 0;
            return (
              <div key={sprint.id} className="rounded-xl border border-[var(--stroke)] bg-white overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <button
                        onClick={() => handleExpand(sprint.id)}
                        className="text-sm font-semibold text-[var(--navy-dark)] hover:text-[var(--primary-blue)] truncate text-left"
                      >
                        {sprint.name}
                      </button>
                      <span className={clsx("rounded-full border px-2 py-0.5 text-[10px] font-semibold", STATUS_STYLE[sprint.status])}>
                        {sprint.status}
                      </span>
                    </div>
                    {sprint.goal && (
                      <div className="text-xs text-[var(--gray-text)] mt-0.5 truncate">{sprint.goal}</div>
                    )}
                    {sprint.start_date && sprint.end_date && (
                      <div className="text-[10px] text-[var(--gray-text)] mt-0.5">
                        {sprint.start_date} — {sprint.end_date}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <select
                      value={sprint.status}
                      onChange={(e) => handleStatusChange(sprint.id, e.target.value)}
                      className="text-xs border border-[var(--stroke)] rounded-lg px-1.5 py-0.5 bg-white outline-none"
                    >
                      {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                    <button
                      onClick={() => handleDelete(sprint.id)}
                      className="text-xs text-[var(--gray-text)] hover:text-red-500"
                    >
                      delete
                    </button>
                  </div>
                </div>

                {/* Progress bar */}
                {(sprint.total_cards ?? 0) > 0 && (
                  <div className="px-4 pb-2">
                    <div className="flex items-center justify-between text-[10px] text-[var(--gray-text)] mb-0.5">
                      <span>{sprint.done_cards}/{sprint.total_cards} done</span>
                      <span>{progress}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-[var(--stroke)]">
                      <div
                        className="h-1.5 rounded-full bg-[var(--primary-blue)] transition-all"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Expanded card list */}
                {expandedId === sprint.id && (
                  <div className="border-t border-[var(--stroke)] px-4 py-2 bg-[var(--surface)] space-y-1">
                    {expandedCards.length === 0 ? (
                      <p className="text-xs text-[var(--gray-text)]">No cards in this sprint.</p>
                    ) : (
                      expandedCards.map((c) => (
                        <div key={c.id} className="flex items-center justify-between text-xs">
                          <span className="text-[var(--navy-dark)] truncate">{c.title}</span>
                          <span className="text-[var(--gray-text)] shrink-0 ml-2">{c.column_title}</span>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
