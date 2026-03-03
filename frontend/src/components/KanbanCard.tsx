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
    if (e.key === "Escape") {
      setEditingField(null);
    } else if (e.key === "Enter" && (editingField !== "details" || !e.shiftKey)) {
      // Title: Enter commits. Details: Enter commits, Shift+Enter inserts newline.
      e.preventDefault();
      commitEdit();
    }
  };

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "group rounded-2xl border-l-[3px] border-l-[var(--accent-yellow)] border border-transparent bg-white px-4 py-4 shadow-[0_12px_24px_rgba(3,33,71,0.08)]",
        "transition-all duration-150",
        "hover:shadow-[0_16px_28px_rgba(3,33,71,0.14)] hover:border-[var(--primary-blue)] hover:-translate-y-0.5",
        isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      <div className="relative">
        <button
          type="button"
          onClick={() => onDelete(card.id)}
          className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full border border-red-200 bg-white text-red-500 opacity-0 shadow-sm transition-opacity group-hover:opacity-100 hover:bg-red-50"
          aria-label={`Delete ${card.title}`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="h-3 w-3">
            <path d="M4.28 3.22a.75.75 0 0 0-1.06 1.06L6.94 8l-3.72 3.72a.75.75 0 1 0 1.06 1.06L8 9.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L9.06 8l3.72-3.72a.75.75 0 0 0-1.06-1.06L8 6.94 4.28 3.22Z" />
          </svg>
        </button>
        <div className="min-w-0">
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
      </div>
    </article>
  );
};
