"use client";

import { useEffect, useState } from "react";
import type { Board, BoardTemplate } from "@/lib/api";
import * as api from "@/lib/api";

interface BoardSelectorProps {
  boards: Board[];
  currentBoardId: number;
  onSelect: (boardId: number) => void;
  onCreate: (name: string, template?: string) => void;
  onRename: (boardId: number, name: string) => void;
  onDelete: (boardId: number) => void;
  onShare?: (boardId: number) => void;
}

export const BoardSelector = ({
  boards,
  currentBoardId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
  onShare,
}: BoardSelectorProps) => {
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [templates, setTemplates] = useState<BoardTemplate[]>([]);
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");

  useEffect(() => {
    if (creating && templates.length === 0) {
      api.listTemplates().then(setTemplates).catch(() => {});
    }
  }, [creating, templates.length]);

  const handleCreate = () => {
    const name = newName.trim();
    if (!name) return;
    onCreate(name, selectedTemplate || undefined);
    setNewName("");
    setSelectedTemplate("");
    setCreating(false);
  };

  const handleRenameSubmit = (boardId: number) => {
    const name = renameValue.trim();
    if (name) onRename(boardId, name);
    setRenamingId(null);
  };

  const currentBoard = boards.find((b) => b.id === currentBoardId);
  const isCurrentBoardOwned = currentBoard && !currentBoard.shared;

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {boards.map((board) => (
        <div key={board.id} className="flex items-center">
          {renamingId === board.id ? (
            <input
              autoFocus
              className="rounded-lg border border-[var(--primary-blue)] px-2 py-1 text-xs font-semibold text-[var(--navy-dark)] outline-none w-28"
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onBlur={() => handleRenameSubmit(board.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleRenameSubmit(board.id);
                if (e.key === "Escape") setRenamingId(null);
              }}
            />
          ) : (
            <div className="flex items-center gap-1">
              <button
                onClick={() => onSelect(board.id)}
                className={`rounded-lg px-3 py-1 text-xs font-semibold transition-colors ${
                  board.id === currentBoardId
                    ? "bg-[var(--primary-blue)] text-white"
                    : "border border-[var(--stroke)] bg-[var(--surface)] text-[var(--navy-dark)] hover:border-[var(--primary-blue)]"
                }`}
              >
                {board.name}
                {board.shared && (
                  <span className="ml-1 text-[10px] opacity-70">(shared)</span>
                )}
              </button>
              {board.id === currentBoardId && (
                <>
                  {onShare && !board.shared && (
                    <button
                      title="Share board"
                      onClick={() => onShare(board.id)}
                      className="text-[var(--gray-text)] hover:text-[var(--secondary-purple)] text-xs px-1"
                    >
                      share
                    </button>
                  )}
                  {!board.shared && (
                    <button
                      title="Rename board"
                      onClick={() => {
                        setRenamingId(board.id);
                        setRenameValue(board.name);
                      }}
                      className="text-[var(--gray-text)] hover:text-[var(--navy-dark)] text-xs px-1"
                    >
                      edit
                    </button>
                  )}
                  {boards.filter((b) => !b.shared).length > 1 && !board.shared && (
                    <button
                      title="Delete board"
                      onClick={() => {
                        if (confirm(`Delete board "${board.name}"? This cannot be undone.`)) {
                          onDelete(board.id);
                        }
                      }}
                      className="text-[var(--gray-text)] hover:text-red-600 text-xs px-1"
                    >
                      x
                    </button>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      ))}

      {creating ? (
        <div className="flex items-center gap-1 flex-wrap">
          <input
            autoFocus
            placeholder="Board name"
            className="rounded-lg border border-[var(--primary-blue)] px-2 py-1 text-xs font-semibold text-[var(--navy-dark)] outline-none w-28"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleCreate();
              if (e.key === "Escape") setCreating(false);
            }}
          />
          {templates.length > 0 && (
            <select
              value={selectedTemplate}
              onChange={(e) => setSelectedTemplate(e.target.value)}
              className="rounded-lg border border-[var(--stroke)] px-2 py-1 text-xs text-[var(--navy-dark)] bg-white outline-none focus:border-[var(--primary-blue)]"
            >
              <option value="">blank</option>
              {templates.map((t) => (
                <option key={t.name} value={t.name}>{t.name}</option>
              ))}
            </select>
          )}
          <button
            onClick={handleCreate}
            className="rounded-lg bg-[var(--primary-blue)] px-2 py-1 text-xs font-semibold text-white"
          >
            Add
          </button>
          <button
            onClick={() => setCreating(false)}
            className="text-[var(--gray-text)] text-xs px-1"
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          onClick={() => setCreating(true)}
          className="rounded-lg border border-dashed border-[var(--stroke)] px-3 py-1 text-xs font-semibold text-[var(--gray-text)] hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)] transition-colors"
        >
          + New Board
        </button>
      )}
    </div>
  );
};
