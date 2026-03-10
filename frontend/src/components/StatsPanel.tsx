"use client";

import { useEffect, useState } from "react";
import type { BoardStats } from "@/lib/api";
import * as api from "@/lib/api";

type StatsPanelProps = {
  boardId: number;
  onClose: () => void;
};

const PRIORITY_COLORS: Record<string, string> = {
  urgent: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-[var(--accent-yellow)]",
  low: "bg-[var(--primary-blue)]",
  none: "bg-[var(--gray-text)]",
};

function Bar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 rounded-full bg-[var(--stroke)] overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-semibold text-[var(--navy-dark)] w-6 text-right">{value}</span>
    </div>
  );
}

export const StatsPanel = ({ boardId, onClose }: StatsPanelProps) => {
  const [stats, setStats] = useState<BoardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getBoardStats(boardId)
      .then(setStats)
      .finally(() => setLoading(false));
  }, [boardId]);

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="relative w-full max-w-lg rounded-2xl border border-[var(--stroke)] bg-white shadow-[var(--shadow)] p-6">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-[var(--gray-text)] hover:text-[var(--navy-dark)] text-lg leading-none"
          aria-label="Close stats"
        >
          x
        </button>
        <h2 className="font-display text-xl font-bold text-[var(--navy-dark)] mb-5">
          Board Statistics
        </h2>

        {loading && (
          <p className="text-sm text-[var(--gray-text)] text-center py-8">Loading...</p>
        )}

        {stats && (
          <div className="space-y-6">
            {/* Summary row */}
            <div className="grid grid-cols-4 gap-3">
              {[
                { label: "Total", value: stats.total_cards, color: "text-[var(--navy-dark)]" },
                { label: "Overdue", value: stats.overdue_count, color: "text-red-500" },
                { label: "Due soon", value: stats.due_soon_count, color: "text-orange-500" },
                { label: "Assigned", value: stats.assigned_count, color: "text-[var(--secondary-purple)]" },
              ].map(({ label, value, color }) => (
                <div key={label} className="rounded-xl border border-[var(--stroke)] bg-[var(--surface)] p-3 text-center">
                  <div className={`text-2xl font-bold font-display ${color}`}>{value}</div>
                  <div className="text-[10px] font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] mt-0.5">{label}</div>
                </div>
              ))}
            </div>

            {/* Cards by column */}
            {Object.keys(stats.cards_by_column).length > 0 && (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)] mb-3">
                  By Column
                </h3>
                <div className="space-y-2">
                  {Object.entries(stats.cards_by_column).map(([col, count]) => (
                    <div key={col}>
                      <div className="flex justify-between text-xs text-[var(--navy-dark)] mb-1">
                        <span className="font-medium truncate">{col}</span>
                      </div>
                      <Bar value={count} max={stats.total_cards || 1} color="bg-[var(--primary-blue)]" />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Cards by priority */}
            {Object.keys(stats.cards_by_priority).length > 0 && (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)] mb-3">
                  By Priority
                </h3>
                <div className="space-y-2">
                  {["urgent", "high", "medium", "low", "none"]
                    .filter((p) => (stats.cards_by_priority[p] ?? 0) > 0)
                    .map((p) => (
                      <div key={p}>
                        <div className="text-xs text-[var(--navy-dark)] mb-1 capitalize">{p}</div>
                        <Bar
                          value={stats.cards_by_priority[p] ?? 0}
                          max={stats.total_cards || 1}
                          color={PRIORITY_COLORS[p] ?? "bg-[var(--gray-text)]"}
                        />
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* Assignment */}
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)] mb-3">
                Assignment
              </h3>
              <div className="space-y-2">
                <div>
                  <div className="text-xs text-[var(--navy-dark)] mb-1">Assigned</div>
                  <Bar value={stats.assigned_count} max={stats.total_cards || 1} color="bg-[var(--secondary-purple)]" />
                </div>
                <div>
                  <div className="text-xs text-[var(--navy-dark)] mb-1">Unassigned</div>
                  <Bar value={stats.unassigned_count} max={stats.total_cards || 1} color="bg-[var(--stroke)]" />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
