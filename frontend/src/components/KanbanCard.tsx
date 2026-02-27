import { useState, type KeyboardEvent } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";

type KanbanCardProps = {
  card: Card;
  onDelete: (cardId: string) => void;
  onEdit: (cardId: string, title: string, details: string) => void;
};

export const KanbanCard = ({ card, onDelete, onEdit }: KanbanCardProps) => {
  const [editingField, setEditingField] = useState<"title" | "details" | null>(null);
  const [editTitle, setEditTitle] = useState(card.title);
  const [editDetails, setEditDetails] = useState(card.details);
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const startEdit = (field: "title" | "details") => {
    setEditTitle(card.title);
    setEditDetails(card.details);
    setEditingField(field);
  };

  const commitEdit = () => {
    const newTitle = editTitle.trim() || card.title;
    const newDetails = editDetails.trim() || card.details;
    if (newTitle !== card.title || newDetails !== card.details) {
      onEdit(card.id, newTitle, newDetails);
    }
    setEditingField(null);
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      commitEdit();
    } else if (e.key === "Escape") {
      setEditingField(null);
    }
  };

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "rounded-2xl border border-transparent bg-white px-4 py-4 shadow-[0_12px_24px_rgba(3,33,71,0.08)]",
        "transition-all duration-150",
        isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          {editingField === "title" ? (
            <input
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onBlur={commitEdit}
              onKeyDown={handleKeyDown}
              className="w-full bg-transparent font-display text-base font-semibold text-[var(--navy-dark)] outline-none ring-1 ring-[var(--primary-blue)] rounded px-1"
              aria-label="Edit card title"
              autoFocus
            />
          ) : (
            <h4
              className="cursor-text font-display text-base font-semibold text-[var(--navy-dark)]"
              onClick={() => startEdit("title")}
              role="button"
              tabIndex={0}
              aria-label="Click to edit title"
            >
              {card.title}
            </h4>
          )}
          {editingField === "details" ? (
            <textarea
              value={editDetails}
              onChange={(e) => setEditDetails(e.target.value)}
              onBlur={commitEdit}
              onKeyDown={handleKeyDown}
              className="mt-2 w-full resize-none bg-transparent text-sm leading-6 text-[var(--gray-text)] outline-none ring-1 ring-[var(--primary-blue)] rounded px-1"
              aria-label="Edit card details"
              rows={2}
              autoFocus
            />
          ) : (
            <p
              className="mt-2 cursor-text text-sm leading-6 text-[var(--gray-text)]"
              onClick={() => startEdit("details")}
              role="button"
              tabIndex={0}
              aria-label="Click to edit details"
            >
              {card.details}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => onDelete(card.id)}
          className="rounded-full border border-transparent px-2 py-1 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--stroke)] hover:text-[var(--navy-dark)]"
          aria-label={`Delete ${card.title}`}
        >
          Remove
        </button>
      </div>
    </article>
  );
};
