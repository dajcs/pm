"use client";

import { useEffect, useState } from "react";
import type { ChecklistItem } from "@/lib/kanban";
import * as api from "@/lib/api";

interface ChecklistPanelProps {
  cardId: string;
  boardId?: number;
  /** Called when total/done counts change (to update the card summary). */
  onCountChange?: (total: number, done: number) => void;
}

export const ChecklistPanel = ({ cardId, boardId, onCountChange }: ChecklistPanelProps) => {
  const [items, setItems] = useState<ChecklistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [newText, setNewText] = useState("");
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editText, setEditText] = useState("");

  useEffect(() => {
    api.getChecklist(cardId, boardId).then((data) => {
      setItems(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [cardId, boardId]);

  const notify = (next: ChecklistItem[]) => {
    const done = next.filter((i) => i.checked).length;
    onCountChange?.(next.length, done);
  };

  const handleAdd = async () => {
    const text = newText.trim();
    if (!text) return;
    try {
      const item = await api.addChecklistItem(cardId, text, boardId);
      const next = [...items, item];
      setItems(next);
      notify(next);
      setNewText("");
      setAdding(false);
    } catch { /* ignore */ }
  };

  const handleToggle = async (item: ChecklistItem) => {
    const next = items.map((i) => i.id === item.id ? { ...i, checked: !i.checked } : i);
    setItems(next);
    notify(next);
    try {
      await api.updateChecklistItem(cardId, item.id, { checked: !item.checked }, boardId);
    } catch {
      setItems(items);
      notify(items);
    }
  };

  const handleEditSubmit = async (item: ChecklistItem) => {
    const text = editText.trim();
    if (!text) { setEditingId(null); return; }
    const next = items.map((i) => i.id === item.id ? { ...i, text } : i);
    setItems(next);
    setEditingId(null);
    try {
      await api.updateChecklistItem(cardId, item.id, { text }, boardId);
    } catch {
      setItems(items);
    }
  };

  const handleDelete = async (item: ChecklistItem) => {
    const next = items.filter((i) => i.id !== item.id);
    setItems(next);
    notify(next);
    try {
      await api.deleteChecklistItem(cardId, item.id, boardId);
    } catch {
      setItems(items);
      notify(items);
    }
  };

  if (loading) return <p className="text-xs text-[var(--gray-text)] mt-2">Loading checklist...</p>;

  const done = items.filter((i) => i.checked).length;

  return (
    <div className="mt-3 border-t border-[var(--stroke)] pt-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)]">
          Checklist {items.length > 0 && `(${done}/${items.length})`}
        </span>
        {items.length > 0 && (
          <div className="h-1.5 flex-1 mx-3 rounded-full bg-[var(--stroke)] overflow-hidden">
            <div
              className="h-full rounded-full bg-[var(--primary-blue)] transition-all"
              style={{ width: `${items.length ? (done / items.length) * 100 : 0}%` }}
            />
          </div>
        )}
      </div>

      <ul className="flex flex-col gap-1">
        {items.map((item) => (
          <li key={item.id} className="flex items-start gap-2 group/item">
            <input
              type="checkbox"
              checked={item.checked}
              onChange={() => handleToggle(item)}
              className="mt-0.5 accent-[var(--primary-blue)]"
            />
            {editingId === item.id ? (
              <input
                autoFocus
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                onBlur={() => handleEditSubmit(item)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleEditSubmit(item);
                  if (e.key === "Escape") setEditingId(null);
                }}
                className="flex-1 rounded border border-[var(--primary-blue)] px-1 py-0.5 text-xs outline-none"
              />
            ) : (
              <span
                className={`flex-1 text-xs cursor-pointer ${item.checked ? "line-through text-[var(--gray-text)]" : "text-[var(--navy-dark)]"}`}
                onClick={() => { setEditingId(item.id); setEditText(item.text); }}
              >
                {item.text}
              </span>
            )}
            <button
              type="button"
              onClick={() => handleDelete(item)}
              className="opacity-0 group-hover/item:opacity-100 text-xs text-[var(--gray-text)] hover:text-red-600 transition-opacity"
              aria-label="Delete item"
            >
              ×
            </button>
          </li>
        ))}
      </ul>

      {adding ? (
        <div className="flex gap-1 mt-2">
          <input
            autoFocus
            placeholder="Add item..."
            value={newText}
            onChange={(e) => setNewText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleAdd();
              if (e.key === "Escape") { setAdding(false); setNewText(""); }
            }}
            className="flex-1 rounded-lg border border-[var(--primary-blue)] px-2 py-1 text-xs outline-none"
          />
          <button
            type="button"
            onClick={handleAdd}
            className="rounded-lg bg-[var(--primary-blue)] px-2 py-1 text-xs font-semibold text-white"
          >
            Add
          </button>
          <button
            type="button"
            onClick={() => { setAdding(false); setNewText(""); }}
            className="text-xs text-[var(--gray-text)] hover:text-[var(--navy-dark)] px-1"
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setAdding(true)}
          className="mt-2 text-xs text-[var(--gray-text)] hover:text-[var(--primary-blue)] transition-colors"
        >
          + Add item
        </button>
      )}
    </div>
  );
};
