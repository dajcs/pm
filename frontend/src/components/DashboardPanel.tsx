"use client";

import { useEffect, useState } from "react";
import type { Dashboard, DashboardEntry } from "@/lib/api";
import * as api from "@/lib/api";

type DashboardPanelProps = {
  onClose: () => void;
  onNavigateBoard?: (boardId: number) => void;
};

const PRIORITY_DOT: Record<string, string> = {
  urgent: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-[var(--accent-yellow)]",
  low: "bg-[var(--primary-blue)]",
  none: "bg-[var(--gray-text)]",
};

function CardRow({ entry, onNavigate }: { entry: DashboardEntry; onNavigate?: (boardId: number) => void }) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 gap-3">
      <div className="flex items-center gap-2 min-w-0">
        <span className={`h-2 w-2 shrink-0 rounded-full ${PRIORITY_DOT[entry.priority] ?? PRIORITY_DOT.none}`} />
        <div className="min-w-0">
          <div className="text-sm font-semibold text-[var(--navy-dark)] truncate">{entry.title}</div>
          <div className="text-xs text-[var(--gray-text)] truncate">
            {entry.board_name} / {entry.column_title}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-xs text-[var(--gray-text)]">{entry.due_date}</span>
        {onNavigate && (
          <button
            onClick={() => onNavigate(entry.board_id)}
            className="text-xs text-[var(--primary-blue)] hover:underline"
          >
            go
          </button>
        )}
      </div>
    </div>
  );
}

export const DashboardPanel = ({ onClose, onNavigateBoard }: DashboardPanelProps) => {
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDashboard()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="relative w-full max-w-lg max-h-[80vh] overflow-y-auto rounded-2xl border border-[var(--stroke)] bg-white shadow-[var(--shadow)] p-6">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-[var(--gray-text)] hover:text-[var(--navy-dark)] text-lg leading-none"
          aria-label="Close dashboard"
        >
          x
        </button>
        <h2 className="font-display text-xl font-bold text-[var(--navy-dark)] mb-5">
          My Dashboard
        </h2>

        {loading && (
          <p className="text-sm text-center text-[var(--gray-text)] py-8">Loading...</p>
        )}

        {data && (
          <div className="space-y-6">
            {/* Summary */}
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-center">
                <div className="text-2xl font-bold font-display text-red-500">{data.total_overdue}</div>
                <div className="text-[10px] font-semibold uppercase tracking-[0.15em] text-red-400 mt-0.5">Overdue</div>
              </div>
              <div className="rounded-xl border border-orange-200 bg-orange-50 p-3 text-center">
                <div className="text-2xl font-bold font-display text-orange-500">{data.total_due_soon}</div>
                <div className="text-[10px] font-semibold uppercase tracking-[0.15em] text-orange-400 mt-0.5">Due soon</div>
              </div>
            </div>

            {/* Overdue */}
            {data.overdue.length > 0 && (
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-red-500 mb-3">
                  Overdue ({data.overdue.length})
                </div>
                <div className="space-y-1.5">
                  {data.overdue.map((e) => (
                    <CardRow key={e.id} entry={e} onNavigate={onNavigateBoard} />
                  ))}
                </div>
              </div>
            )}

            {/* Due soon */}
            {data.due_soon.length > 0 && (
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-orange-500 mb-3">
                  Due soon ({data.due_soon.length})
                </div>
                <div className="space-y-1.5">
                  {data.due_soon.map((e) => (
                    <CardRow key={e.id} entry={e} onNavigate={onNavigateBoard} />
                  ))}
                </div>
              </div>
            )}

            {data.total_overdue === 0 && data.total_due_soon === 0 && (
              <div className="text-center py-6 text-sm text-[var(--gray-text)]">
                All clear. No overdue or upcoming due dates.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
