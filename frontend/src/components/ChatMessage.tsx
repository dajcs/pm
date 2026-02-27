"use client";

import { useState, useRef, useEffect } from "react";

export type ChatMsg = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

interface ChatMessageProps {
  message: ChatMsg;
  onEdit?: (id: string, content: string) => void;
  onDelete?: (id: string) => void;
}

export const ChatMessage = ({ message, onEdit, onDelete }: ChatMessageProps) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(message.content);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const isUser = message.role === "user";

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.selectionStart = inputRef.current.value.length;
    }
  }, [editing]);

  const handleSave = () => {
    const trimmed = draft.trim();
    if (trimmed && trimmed !== message.content) {
      onEdit?.(message.id, trimmed);
    }
    setEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSave();
    }
    if (e.key === "Escape") {
      setDraft(message.content);
      setEditing(false);
    }
  };

  return (
    <div
      data-testid={`chat-msg-${message.id}`}
      className={`group flex flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}
    >
      <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
        {isUser ? "You" : "AI"}
      </span>

      {editing ? (
        <textarea
          ref={inputRef}
          aria-label="Edit message"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={handleSave}
          onKeyDown={handleKeyDown}
          rows={2}
          className="w-full resize-none rounded-xl border border-[var(--primary-blue)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none"
        />
      ) : (
        <div
          className={`max-w-[95%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? "bg-[var(--primary-blue)] text-white"
              : "border border-[var(--stroke)] bg-white text-[var(--navy-dark)]"
          }`}
        >
          {message.content}
        </div>
      )}

      {isUser && !editing && (
        <div className="flex gap-2 opacity-0 transition-opacity group-hover:opacity-100">
          <button
            onClick={() => {
              setDraft(message.content);
              setEditing(true);
            }}
            className="text-[10px] font-semibold uppercase tracking-wider text-[var(--gray-text)] hover:text-[var(--primary-blue)]"
          >
            Edit
          </button>
          <button
            onClick={() => onDelete?.(message.id)}
            className="text-[10px] font-semibold uppercase tracking-wider text-[var(--gray-text)] hover:text-red-500"
          >
            Delete
          </button>
        </div>
      )}
    </div>
  );
};
