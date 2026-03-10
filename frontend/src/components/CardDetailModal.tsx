"use client";

import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";
import { ChecklistPanel } from "@/components/ChecklistPanel";
import { CommentsPanel } from "@/components/CommentsPanel";
import { DependenciesPanel } from "@/components/DependenciesPanel";
import { TimeTrackingPanel } from "@/components/TimeTrackingPanel";
import { CardSprintPanel } from "@/components/CardSprintPanel";

const PRIORITIES = ["none", "low", "medium", "high", "urgent"];
const PRIORITY_STYLES: Record<string, { dot: string }> = {
  none:   { dot: "bg-[var(--gray-text)]" },
  low:    { dot: "bg-[var(--primary-blue)]" },
  medium: { dot: "bg-[var(--accent-yellow)]" },
  high:   { dot: "bg-orange-500" },
  urgent: { dot: "bg-red-500" },
};
const LABEL_OPTIONS = ["bug", "feature", "improvement", "docs", "testing", "blocked"];
const LABEL_COLORS: Record<string, string> = {
  bug: "bg-red-100 text-red-700 border-red-200",
  feature: "bg-blue-100 text-blue-700 border-blue-200",
  improvement: "bg-purple-100 text-purple-700 border-purple-200",
  docs: "bg-gray-100 text-gray-700 border-gray-200",
  testing: "bg-green-100 text-green-700 border-green-200",
  blocked: "bg-orange-100 text-orange-700 border-orange-200",
};

type CardDetailModalProps = {
  card: Card;
  columnTitle: string;
  boardId?: number;
  boardMembers?: string[];
  allCardTitles?: Record<string, string>;
  onClose: () => void;
  onEdit: (cardId: string, title: string, details: string) => void;
  onUpdatePriority?: (cardId: string, priority: string) => void;
  onUpdateDueDate?: (cardId: string, dueDate: string | null) => void;
  onUpdateLabels?: (cardId: string, labels: string[]) => void;
  onAssign?: (cardId: string, username: string | null) => void;
  onChecklistCountChange?: (cardId: string, total: number, done: number) => void;
  onCommentCountChange?: (cardId: string, count: number) => void;
  onArchive?: (cardId: string) => void;
  onDuplicate?: (cardId: string) => void;
};

export const CardDetailModal = ({
  card,
  columnTitle,
  boardId,
  boardMembers,
  allCardTitles,
  onClose,
  onEdit,
  onUpdatePriority,
  onUpdateDueDate,
  onUpdateLabels,
  onAssign,
  onChecklistCountChange,
  onCommentCountChange,
  onArchive,
  onDuplicate,
}: CardDetailModalProps) => {
  const [editTitle, setEditTitle] = useState(card.title);
  const [editDetails, setEditDetails] = useState(card.details);
  const [editingTitle, setEditingTitle] = useState(false);
  const [editingDetails, setEditingDetails] = useState(false);
  const [editDueDate, setEditDueDate] = useState(card.due_date ?? "");
  const titleRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const commitTitle = () => {
    const t = editTitle.trim() || card.title;
    if (t !== card.title) onEdit(card.id, t, card.details);
    setEditingTitle(false);
  };

  const commitDetails = () => {
    const d = editDetails.trim() || card.details;
    if (d !== card.details) onEdit(card.id, card.title, d);
    setEditingDetails(false);
  };

  const commitDueDate = () => {
    const val = editDueDate.trim() || null;
    if (val !== (card.due_date ?? null)) {
      onUpdateDueDate?.(card.id, val);
    }
  };

  const priority = card.priority ?? "none";
  const labels = card.labels ?? [];

  const cyclePriority = () => {
    const idx = PRIORITIES.indexOf(priority);
    onUpdatePriority?.(card.id, PRIORITIES[(idx + 1) % PRIORITIES.length]);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-[var(--stroke)] bg-white shadow-[var(--shadow)]">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-[var(--stroke)] px-6 py-4 flex items-center justify-between z-10">
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
            {columnTitle}
          </span>
          <div className="flex items-center gap-2">
            {onDuplicate && (
              <button
                onClick={() => { onDuplicate(card.id); onClose(); }}
                className="rounded-lg border border-[var(--stroke)] px-3 py-1 text-xs text-[var(--gray-text)] hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)] transition-colors"
                title="Duplicate card"
              >
                duplicate
              </button>
            )}
            {onArchive && (
              <button
                onClick={() => { onArchive(card.id); onClose(); }}
                className="rounded-lg border border-[var(--stroke)] px-3 py-1 text-xs text-[var(--gray-text)] hover:border-orange-500 hover:text-orange-500 transition-colors"
                title="Archive card"
              >
                archive
              </button>
            )}
            <button
              onClick={onClose}
              className="text-[var(--gray-text)] hover:text-[var(--navy-dark)] text-lg leading-none px-1"
              aria-label="Close"
            >
              x
            </button>
          </div>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* Title */}
          {editingTitle ? (
            <input
              ref={titleRef}
              autoFocus
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onBlur={commitTitle}
              onKeyDown={(e) => {
                if (e.key === "Enter") commitTitle();
                if (e.key === "Escape") { setEditTitle(card.title); setEditingTitle(false); }
              }}
              className="w-full font-display text-2xl font-bold text-[var(--navy-dark)] bg-transparent border-b-2 border-[var(--primary-blue)] outline-none pb-1"
            />
          ) : (
            <h2
              className="font-display text-2xl font-bold text-[var(--navy-dark)] cursor-text hover:text-[var(--primary-blue)] transition-colors"
              onClick={() => { setEditTitle(card.title); setEditingTitle(true); }}
              title="Click to edit title"
            >
              {card.title}
            </h2>
          )}

          {/* Metadata row */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Priority */}
            <button
              onClick={cyclePriority}
              className="flex items-center gap-1.5 rounded-full border border-[var(--stroke)] px-3 py-1 text-xs font-medium text-[var(--navy-dark)] hover:border-[var(--primary-blue)] transition-colors"
              title={`Priority: ${priority} (click to cycle)`}
            >
              <span className={clsx("h-2 w-2 rounded-full", PRIORITY_STYLES[priority]?.dot ?? "bg-[var(--gray-text)]")} />
              {priority}
            </button>

            {/* Due date */}
            <div className="flex items-center gap-1">
              <span className="text-xs text-[var(--gray-text)]">Due:</span>
              <input
                type="date"
                value={editDueDate}
                onChange={(e) => setEditDueDate(e.target.value)}
                onBlur={commitDueDate}
                className="text-xs border border-[var(--stroke)] rounded-lg px-2 py-0.5 outline-none focus:border-[var(--primary-blue)] text-[var(--navy-dark)]"
              />
              {editDueDate && (
                <button
                  onClick={() => { setEditDueDate(""); onUpdateDueDate?.(card.id, null); }}
                  className="text-xs text-[var(--gray-text)] hover:text-red-500"
                  title="Clear due date"
                >
                  x
                </button>
              )}
            </div>

            {/* Assignee */}
            {onAssign && (
              <div className="flex items-center gap-1">
                <span className="text-xs text-[var(--gray-text)]">Assigned:</span>
                <select
                  value={card.assigned_to ?? ""}
                  onChange={(e) => onAssign(card.id, e.target.value || null)}
                  className="text-xs border border-[var(--stroke)] rounded-lg px-2 py-0.5 outline-none focus:border-[var(--primary-blue)] text-[var(--navy-dark)] bg-white"
                >
                  <option value="">Unassigned</option>
                  {(boardMembers ?? []).map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Labels */}
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] mb-2">Labels</div>
            <div className="flex flex-wrap gap-1.5">
              {LABEL_OPTIONS.map((label) => {
                const active = labels.includes(label);
                return (
                  <button
                    key={label}
                    onClick={() => {
                      const next = active ? labels.filter((l) => l !== label) : [...labels, label];
                      onUpdateLabels?.(card.id, next);
                    }}
                    className={clsx(
                      "rounded-full border px-3 py-0.5 text-xs font-semibold transition-opacity",
                      LABEL_COLORS[label] ?? "bg-gray-100 text-gray-700 border-gray-200",
                      active ? "opacity-100" : "opacity-30 hover:opacity-60"
                    )}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Details */}
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] mb-2">Details</div>
            {editingDetails ? (
              <textarea
                autoFocus
                value={editDetails}
                onChange={(e) => setEditDetails(e.target.value)}
                onBlur={commitDetails}
                onKeyDown={(e) => {
                  if (e.key === "Escape") { setEditDetails(card.details); setEditingDetails(false); }
                }}
                rows={5}
                className="w-full resize-y rounded-xl border border-[var(--primary-blue)] bg-[var(--surface)] p-3 text-sm leading-6 text-[var(--navy-dark)] outline-none"
              />
            ) : (
              <div
                onClick={() => { setEditDetails(card.details); setEditingDetails(true); }}
                className="min-h-[80px] cursor-text rounded-xl border border-[var(--stroke)] bg-[var(--surface)] p-3 text-sm leading-6 text-[var(--gray-text)] hover:border-[var(--primary-blue)] transition-colors whitespace-pre-wrap"
                title="Click to edit"
              >
                {card.details || "No details yet."}
              </div>
            )}
          </div>

          {/* Checklist */}
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] mb-2">
              Checklist
              {(card.checklist_total ?? 0) > 0 && (
                <span className="ml-2 normal-case font-normal text-[var(--navy-dark)]">
                  {card.checklist_done ?? 0}/{card.checklist_total}
                </span>
              )}
            </div>
            <ChecklistPanel
              cardId={card.id}
              boardId={boardId}
              onCountChange={(total, done) => onChecklistCountChange?.(card.id, total, done)}
            />
          </div>

          {/* Dependencies */}
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] mb-2">
              Dependencies
            </div>
            <DependenciesPanel cardId={card.id} boardId={boardId} allCardTitles={allCardTitles} />
          </div>

          {/* Sprint */}
          {boardId && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] mb-2">
                Sprints
              </div>
              <CardSprintPanel cardId={card.id} boardId={boardId} />
            </div>
          )}

          {/* Time Tracking */}
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] mb-2">
              Time Logged
            </div>
            <TimeTrackingPanel cardId={card.id} boardId={boardId} />
          </div>

          {/* Comments */}
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] mb-2">
              Comments
              {(card.comment_count ?? 0) > 0 && (
                <span className="ml-2 normal-case font-normal text-[var(--navy-dark)]">
                  {card.comment_count}
                </span>
              )}
            </div>
            <CommentsPanel
              cardId={card.id}
              boardId={boardId}
              onCountChange={(count) => onCommentCountChange?.(card.id, count)}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
