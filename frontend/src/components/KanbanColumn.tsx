import { useState, useEffect } from "react";
import clsx from "clsx";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { Card, Column } from "@/lib/kanban";
import { KanbanCard } from "@/components/KanbanCard";
import { NewCardForm } from "@/components/NewCardForm";

type KanbanColumnProps = {
  column: Column;
  cards: Card[];
  boardId?: number;
  isHighlighted?: boolean;
  onRename: (columnId: string, title: string) => void;
  onAddCard: (columnId: string, title: string, details: string) => void;
  onDeleteCard: (columnId: string, cardId: string) => void;
  onArchiveCard?: (columnId: string, cardId: string) => void;
  onEditCard: (cardId: string, title: string, details: string) => void;
  onDeleteColumn?: (columnId: string) => void;
  onUpdatePriority?: (cardId: string, priority: string) => void;
  onUpdateDueDate?: (cardId: string, dueDate: string | null) => void;
  onUpdateLabels?: (cardId: string, labels: string[]) => void;
  onSetWipLimit?: (columnId: string, wipLimit: number | null) => void;
  onChecklistCountChange?: (cardId: string, total: number, done: number) => void;
  onCommentCountChange?: (cardId: string, count: number) => void;
  onRegisterAddTrigger?: (trigger: () => void) => void;
  onAssign?: (cardId: string, username: string | null) => void;
  boardMembers?: string[];
};

export const KanbanColumn = ({
  column,
  cards,
  boardId,
  isHighlighted,
  onRename,
  onAddCard,
  onDeleteCard,
  onEditCard,
  onDeleteColumn,
  onUpdatePriority,
  onUpdateDueDate,
  onUpdateLabels,
  onSetWipLimit,
  onChecklistCountChange,
  onCommentCountChange,
  onArchiveCard,
  onRegisterAddTrigger,
  onAssign,
  boardMembers,
}: KanbanColumnProps) => {
  const { setNodeRef } = useDroppable({ id: column.id });
  const [localTitle, setLocalTitle] = useState(column.title);
  const [editingWip, setEditingWip] = useState(false);
  const [wipInput, setWipInput] = useState("");

  // Sync local title if column prop changes (e.g. after API rollback)
  useEffect(() => {
    setLocalTitle(column.title);
  }, [column.title]);

  const commitRename = () => {
    const trimmed = localTitle.trim();
    if (!trimmed) {
      setLocalTitle(column.title);
    } else if (trimmed !== column.title) {
      onRename(column.id, trimmed);
    }
  };

  return (
    <section
      ref={setNodeRef}
      className={clsx(
        "flex min-h-[480px] flex-col rounded-2xl border border-[var(--stroke)] bg-[var(--surface-strong)] p-3 shadow-[var(--shadow)] transition",
        isHighlighted && "ring-2 ring-[var(--accent-yellow)] bg-[var(--accent-yellow)]/5"
      )}
      data-testid={`column-${column.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="w-full">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="h-1.5 w-12 rounded-full bg-[var(--secondary-purple)]" />
            {column.wip_limit ? (
              <span className={`text-xs font-semibold uppercase tracking-[0.15em] ${cards.length > column.wip_limit ? "text-red-500" : "text-[var(--navy-dark)]"}`}>
                {cards.length}/{column.wip_limit}
              </span>
            ) : (
              <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]">
                {cards.length} cards
              </span>
            )}
            <div className="ml-auto flex items-center gap-1">
              {onSetWipLimit && (
                editingWip ? (
                  <input
                    autoFocus
                    type="number"
                    min={1}
                    placeholder="limit"
                    value={wipInput}
                    onChange={(e) => setWipInput(e.target.value)}
                    onBlur={() => {
                      const n = parseInt(wipInput, 10);
                      onSetWipLimit(column.id, isNaN(n) || n < 1 ? null : n);
                      setEditingWip(false);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") e.currentTarget.blur();
                      if (e.key === "Escape") { setEditingWip(false); }
                    }}
                    className="w-14 rounded border border-[var(--primary-blue)] px-1 py-0.5 text-xs outline-none"
                  />
                ) : (
                  <button
                    title={column.wip_limit ? `WIP limit: ${column.wip_limit} (click to change)` : "Set WIP limit"}
                    onClick={() => { setWipInput(column.wip_limit?.toString() ?? ""); setEditingWip(true); }}
                    className="text-xs text-[var(--gray-text)] hover:text-[var(--navy-dark)] transition-colors px-0.5"
                  >
                    wip
                  </button>
                )
              )}
              {onDeleteColumn && (
                <button
                  title="Delete column"
                  onClick={() => {
                    if (confirm(`Delete column "${column.title}" and all its cards?`)) {
                      onDeleteColumn(column.id);
                    }
                  }}
                  className="text-xs text-[var(--gray-text)] hover:text-red-600 transition-colors px-0.5"
                >
                  del
                </button>
              )}
            </div>
          </div>
          <input
            value={localTitle}
            onChange={(e) => setLocalTitle(e.target.value)}
            onBlur={commitRename}
            onKeyDown={(e) => {
              if (e.key === "Enter") e.currentTarget.blur();
            }}
            className="mt-3 w-full bg-transparent font-display text-xl font-bold text-[var(--navy-dark)] outline-none"
            aria-label="Column title"
          />
        </div>
      </div>
      <div className="mt-3 flex flex-1 flex-col gap-2">
        <SortableContext items={column.cardIds} strategy={verticalListSortingStrategy}>
          {cards.map((card) => (
            <KanbanCard
              key={card.id}
              card={card}
              onDelete={(cardId) => onDeleteCard(column.id, cardId)}
              onArchive={onArchiveCard ? (cardId) => onArchiveCard(column.id, cardId) : undefined}
              onEdit={onEditCard}
              boardId={boardId}
              onUpdatePriority={onUpdatePriority}
              onUpdateDueDate={onUpdateDueDate}
              onUpdateLabels={onUpdateLabels}
              onChecklistCountChange={onChecklistCountChange}
              onCommentCountChange={onCommentCountChange}
              onAssign={onAssign}
              boardMembers={boardMembers}
            />
          ))}
        </SortableContext>
        {cards.length === 0 && (
          <div className="flex flex-1 items-center justify-center rounded-2xl border border-dashed border-[var(--stroke)] px-3 py-6 text-center text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
            Drop a card here
          </div>
        )}
      </div>
      <NewCardForm
        onAdd={(title, details) => onAddCard(column.id, title, details)}
        onRegisterOpenTrigger={onRegisterAddTrigger}
      />
    </section>
  );
};
