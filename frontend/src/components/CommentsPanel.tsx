"use client";

import { useEffect, useState } from "react";
import type { Comment } from "@/lib/kanban";
import { formatRelative } from "@/lib/constants";
import * as api from "@/lib/api";

interface CommentsPanelProps {
  cardId: string;
  boardId?: number;
  onCountChange?: (count: number) => void;
}

export const CommentsPanel = ({ cardId, boardId, onCountChange }: CommentsPanelProps) => {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [newText, setNewText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.getComments(cardId, boardId).then((data) => {
      setComments(data);
      onCountChange?.(data.length);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [cardId, boardId]);

  const handleAdd = async () => {
    const text = newText.trim();
    if (!text || submitting) return;
    setSubmitting(true);
    try {
      const comment = await api.addComment(cardId, text, boardId);
      const next = [...comments, comment];
      setComments(next);
      onCountChange?.(next.length);
      setNewText("");
    } catch { /* ignore */ }
    setSubmitting(false);
  };

  const handleDelete = async (comment: Comment) => {
    try {
      await api.deleteComment(cardId, comment.id, boardId);
      const next = comments.filter((c) => c.id !== comment.id);
      setComments(next);
      onCountChange?.(next.length);
    } catch { /* ignore */ }
  };

  if (loading) return <p className="text-xs text-[var(--gray-text)] mt-2">Loading comments...</p>;

  return (
    <div className="mt-3 border-t border-[var(--stroke)] pt-3">
      <span className="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)]">
        Comments {comments.length > 0 && `(${comments.length})`}
      </span>

      <ul className="mt-2 flex flex-col gap-2">
        {comments.map((c) => (
          <li key={c.id} className="group/comment flex gap-2">
            <div className="flex-1 rounded-xl bg-[var(--surface)] px-3 py-2">
              <div className="flex items-center justify-between gap-1">
                <span className="text-[11px] font-semibold text-[var(--navy-dark)]">{c.username}</span>
                <span className="text-[10px] text-[var(--gray-text)]">{formatRelative(c.created_at)}</span>
              </div>
              <p className="mt-0.5 text-xs text-[var(--navy-dark)] whitespace-pre-wrap">{c.text}</p>
            </div>
            <button
              type="button"
              onClick={() => handleDelete(c)}
              className="self-start opacity-0 group-hover/comment:opacity-100 text-xs text-[var(--gray-text)] hover:text-red-600 transition-opacity pt-2"
              aria-label="Delete comment"
            >
              ×
            </button>
          </li>
        ))}
      </ul>

      <div className="mt-2 flex gap-1">
        <textarea
          placeholder="Add a comment..."
          value={newText}
          onChange={(e) => setNewText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleAdd();
            }
          }}
          rows={2}
          className="flex-1 resize-none rounded-lg border border-[var(--stroke)] bg-[var(--surface)] px-2 py-1 text-xs outline-none focus:border-[var(--primary-blue)]"
        />
        <button
          type="button"
          onClick={handleAdd}
          disabled={!newText.trim() || submitting}
          className="self-end rounded-lg bg-[var(--primary-blue)] px-2 py-1 text-xs font-semibold text-white disabled:opacity-40"
        >
          Post
        </button>
      </div>
    </div>
  );
};
