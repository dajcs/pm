"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  pointerWithin,
  closestCenter,
  type CollisionDetection,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
} from "@dnd-kit/core";

/** Use pointer position first; fall back to closest center when pointer is in a gap. */
const collisionDetection: CollisionDetection = (args) => {
  const pointer = pointerWithin(args);
  if (pointer.length > 0) return pointer;
  return closestCenter(args);
};
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { BoardSelector } from "@/components/BoardSelector";
import { AccountModal } from "@/components/AccountModal";
import { ArchivePanel } from "@/components/ArchivePanel";
import { ActivityFeed } from "@/components/ActivityFeed";
import { StatsPanel } from "@/components/StatsPanel";
import { CardDetailModal } from "@/components/CardDetailModal";
import { BoardSharePanel } from "@/components/BoardSharePanel";
import { DashboardPanel } from "@/components/DashboardPanel";
import { SprintPanel } from "@/components/SprintPanel";
import { moveCard, moveColumn, type BoardData, type Card } from "@/lib/kanban";
import type { Board } from "@/lib/api";
import * as api from "@/lib/api";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";

interface KanbanBoardProps {
  onLogout?: () => void;
  username?: string;
  /** Supply initial board data (used in tests to skip API fetch). */
  initialBoard?: BoardData;
  /** Board data from an external update (e.g. AI mutation). Applied in-place. */
  pendingBoard?: BoardData | null;
  /** Called after pendingBoard has been applied to internal state. */
  onPendingBoardApplied?: () => void;
  /** Current board id. */
  boardId?: number;
  /** List of boards for the selector. */
  boards?: Board[];
  onBoardSelect?: (boardId: number) => void;
  onBoardCreate?: (name: string, template?: string) => void;
  onBoardRename?: (boardId: number, name: string) => void;
  onBoardDelete?: (boardId: number) => void;
}

export const KanbanBoard = ({
  onLogout,
  username,
  initialBoard,
  pendingBoard,
  onPendingBoardApplied,
  boardId,
  boards,
  onBoardSelect,
  onBoardCreate,
  onBoardRename,
  onBoardDelete,
}: KanbanBoardProps) => {
  const [board, setBoard] = useState<BoardData | null>(initialBoard ?? null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [overColumnId, setOverColumnId] = useState<string | null>(null);
  const [loading, setLoading] = useState(!initialBoard);
  const [error, setError] = useState<string | null>(null);
  const [addingColumn, setAddingColumn] = useState(false);
  const [newColumnTitle, setNewColumnTitle] = useState("");
  const [filterPriority, setFilterPriority] = useState<string | null>(null);
  const [filterOverdue, setFilterOverdue] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [showAccount, setShowAccount] = useState(false);
  const [showArchive, setShowArchive] = useState(false);
  const [showActivity, setShowActivity] = useState(false);
  const [showStats, setShowStats] = useState(false);
  const [showShare, setShowShare] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [showSprints, setShowSprints] = useState(false);
  const [detailCardId, setDetailCardId] = useState<string | null>(null);
  const [boardMembers, setBoardMembers] = useState<string[]>([]);
  const errorTimer = useRef<ReturnType<typeof setTimeout>>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const firstAddCardRef = useRef<(() => void) | null>(null);

  const showError = useCallback((msg: string) => {
    setError(msg);
    if (errorTimer.current) clearTimeout(errorTimer.current);
    errorTimer.current = setTimeout(() => setError(null), 4000);
  }, []);

  useKeyboardShortcuts({
    onFocusSearch: () => searchInputRef.current?.focus(),
    onEscape: () => {
      setShowAccount(false);
      setShowArchive(false);
      setShowActivity(false);
      setShowStats(false);
      setShowShare(false);
      setShowDashboard(false);
      setShowSprints(false);
      setDetailCardId(null);
      setAddingColumn(false);
      searchInputRef.current?.blur();
    },
    onAddCard: () => firstAddCardRef.current?.(),
  });

  const handleBulkArchive = (columnId: string) => {
    if (!board || !boardId) return;
    const prev = board;
    const col = board.columns.find((c) => c.id === columnId);
    if (!col) return;
    const archivedIds = new Set(col.cardIds);
    setBoard({
      ...board,
      columns: board.columns.map((c) =>
        c.id === columnId ? { ...c, cardIds: [] } : c
      ),
      cards: Object.fromEntries(
        Object.entries(board.cards).filter(([id]) => !archivedIds.has(id))
      ),
    });
    api.archiveColumnCards(columnId, boardId).catch((err) => {
      setBoard(prev);
      showError(err.message);
    });
  };

  const handleDuplicateCard = (cardId: string) => {
    if (!board) return;
    api.duplicateCard(cardId, boardId).then((dup) => {
      setBoard((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          cards: { ...prev.cards, [dup.id]: { id: dup.id, title: dup.title, details: dup.details, due_date: dup.due_date, priority: dup.priority, labels: dup.labels } },
          columns: prev.columns.map((col) =>
            col.id === dup.column_id ? { ...col, cardIds: [...col.cardIds, dup.id] } : col
          ),
        };
      });
    }).catch((err) => showError(err.message));
  };

  const handleExport = () => {
    if (!boardId) return;
    api.exportBoard(boardId).then((data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `board-export-${boardId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }).catch((err) => showError(err.message));
  };

  // Fetch board on mount or when boardId changes (skip if initialBoard provided)
  useEffect(() => {
    if (initialBoard) return;
    let cancelled = false;
    setLoading(true);
    api
      .fetchBoard(boardId)
      .then((data) => {
        if (!cancelled) setBoard(data);
      })
      .catch((err) => {
        if (!cancelled) showError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [initialBoard, boardId, showError]);

  // Fetch board members when boardId is known
  useEffect(() => {
    if (!boardId) return;
    api.getBoardMembers(boardId).then(setBoardMembers).catch(() => {});
  }, [boardId]);

  // Apply external board update in-place (avoids full remount)
  useEffect(() => {
    if (pendingBoard) {
      setBoard(pendingBoard);
      onPendingBoardApplied?.();
    }
  }, [pendingBoard, onPendingBoardApplied]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const findColumnForItem = useCallback(
    (itemId: string): string | null => {
      if (!board) return null;
      const col = board.columns.find((c) => c.id === itemId);
      if (col) return col.id;
      const parent = board.columns.find((c) => c.cardIds.includes(itemId));
      return parent?.id ?? null;
    },
    [board]
  );

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      const id = event.active.id as string;
      setActiveCardId(id);
      setOverColumnId(findColumnForItem(id));
    },
    [findColumnForItem]
  );

  const handleDragOver = useCallback(
    (event: DragOverEvent) => {
      const overId = event.over?.id as string | undefined;
      setOverColumnId(overId ? findColumnForItem(overId) : null);
    },
    [findColumnForItem]
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      setActiveCardId(null);
      setOverColumnId(null);

      if (!over || active.id === over.id || !board) return;

      const activeIsColumn = board.columns.some((c) => c.id === active.id);

      // Detect cross-column card move for activity logging
      if (!activeIsColumn && boardId) {
        const fromCol = board.columns.find((c) => c.cardIds.includes(active.id as string));
        const toColId = board.columns.find((c) => c.id === over.id)?.id
          ?? board.columns.find((c) => c.cardIds.includes(over.id as string))?.id;
        const toCol = board.columns.find((c) => c.id === toColId);
        if (fromCol && toCol && fromCol.id !== toCol.id) {
          const card = board.cards[active.id as string];
          const action = `moved card "${card?.title ?? active.id}" from ${fromCol.title} to ${toCol.title}`;
          api.logBoardActivity(boardId, action).catch(() => { /* non-critical */ });
        }
      }

      const newColumns = activeIsColumn
        ? moveColumn(board.columns, active.id as string, over.id as string)
        : moveCard(board.columns, active.id as string, over.id as string);

      const updated = { ...board, columns: newColumns };
      setBoard(updated);

      api.saveColumnsOrder(updated, boardId).catch((err) => {
        setBoard(board);
        showError(err.message);
      });
    },
    [board, boardId, showError]
  );

  const handleRenameColumn = (columnId: string, title: string) => {
    if (!board) return;
    const prev = board;
    setBoard({
      ...board,
      columns: board.columns.map((col) =>
        col.id === columnId ? { ...col, title } : col
      ),
    });

    api.renameColumn(columnId, title, boardId).catch((err) => {
      setBoard(prev);
      showError(err.message);
    });
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    if (!board) return;
    const cardDetails = details || "No details yet.";

    api
      .createCard(columnId, title, cardDetails, boardId)
      .then((card) => {
        setBoard((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            cards: {
              ...prev.cards,
              [card.id]: { id: card.id, title: card.title, details: card.details },
            },
            columns: prev.columns.map((col) =>
              col.id === columnId
                ? { ...col, cardIds: [...col.cardIds, card.id] }
                : col
            ),
          };
        });
      })
      .catch((err) => showError(err.message));
  };

  const removeCardFromState = (cardId: string) => {
    setBoard((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        cards: Object.fromEntries(Object.entries(prev.cards).filter(([id]) => id !== cardId)),
        columns: prev.columns.map((col) => ({
          ...col,
          cardIds: col.cardIds.filter((id) => id !== cardId),
        })),
      };
    });
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    if (!board) return;
    const prev = board;
    removeCardFromState(cardId);
    api.deleteCard(cardId, boardId).catch((err) => {
      setBoard(prev);
      showError(err.message);
    });
  };

  const handleArchiveCard = (columnId: string, cardId: string) => {
    if (!board) return;
    const prev = board;
    removeCardFromState(cardId);
    api.archiveCard(cardId, boardId).catch((err) => {
      setBoard(prev);
      showError(err.message);
    });
  };

  const handleEditCard = (cardId: string, title: string, details: string) => {
    if (!board) return;
    const existing = board.cards[cardId];
    const prev = board;
    setBoard({
      ...board,
      cards: {
        ...board.cards,
        [cardId]: { ...existing, title, details },
      },
    });

    // Only send fields that actually changed
    const fields: { title?: string; details?: string } = {};
    if (title !== existing?.title) fields.title = title;
    if (details !== existing?.details) fields.details = details;

    api.updateCard(cardId, fields, boardId).catch((err) => {
      setBoard(prev);
      showError(err.message);
    });
  };

  const handleUpdatePriority = (cardId: string, priority: string) => {
    if (!board) return;
    const existing = board.cards[cardId];
    const prev = board;
    setBoard({
      ...board,
      cards: { ...board.cards, [cardId]: { ...existing, priority } },
    });
    api.updateCard(cardId, { priority }, boardId).catch((err) => {
      setBoard(prev);
      showError(err.message);
    });
  };

  const handleUpdateDueDate = (cardId: string, dueDate: string | null) => {
    if (!board) return;
    const existing = board.cards[cardId];
    const prev = board;
    setBoard({
      ...board,
      cards: { ...board.cards, [cardId]: { ...existing, due_date: dueDate } },
    });
    api.updateCard(cardId, { due_date: dueDate }, boardId).catch((err) => {
      setBoard(prev);
      showError(err.message);
    });
  };

  const handleUpdateLabels = (cardId: string, labels: string[]) => {
    if (!board) return;
    const prev = board;
    setBoard({ ...board, cards: { ...board.cards, [cardId]: { ...board.cards[cardId], labels } } });
    api.updateCard(cardId, { labels }, boardId).catch((err) => { setBoard(prev); showError(err.message); });
  };

  const handleChecklistCountChange = (cardId: string, total: number, done: number) => {
    setBoard((prev) => {
      if (!prev) return prev;
      const card = prev.cards[cardId];
      if (!card) return prev;
      return { ...prev, cards: { ...prev.cards, [cardId]: { ...card, checklist_total: total, checklist_done: done } } };
    });
  };

  const handleAssign = (cardId: string, username: string | null) => {
    if (!board) return;
    const prev = board;
    setBoard((b) => {
      if (!b) return b;
      const card = b.cards[cardId];
      if (!card) return b;
      return { ...b, cards: { ...b.cards, [cardId]: { ...card, assigned_to: username } } };
    });
    api.updateCard(cardId, { assigned_to: username }, boardId).catch((err) => {
      setBoard(prev);
      showError(err.message);
    });
  };

  const handleCommentCountChange = (cardId: string, count: number) => {
    setBoard((prev) => {
      if (!prev) return prev;
      const card = prev.cards[cardId];
      if (!card) return prev;
      return { ...prev, cards: { ...prev.cards, [cardId]: { ...card, comment_count: count } } };
    });
  };

  const handleSetWipLimit = (columnId: string, wipLimit: number | null) => {
    if (!board) return;
    const prev = board;
    setBoard({
      ...board,
      columns: board.columns.map((c) => c.id === columnId ? { ...c, wip_limit: wipLimit } : c),
    });
    api.setColumnWipLimit(columnId, wipLimit, boardId).catch((err) => { setBoard(prev); showError(err.message); });
  };

  const handleAddColumn = () => {
    const title = newColumnTitle.trim();
    if (!title || !board) return;

    api
      .addColumn(title, boardId)
      .then((col) => {
        setBoard((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            columns: [...prev.columns, { id: col.id, title: col.title, cardIds: [] }],
          };
        });
        setNewColumnTitle("");
        setAddingColumn(false);
      })
      .catch((err) => showError(err.message));
  };

  const handleDeleteColumn = (columnId: string) => {
    if (!board) return;
    const prev = board;

    // Remove the column and its cards from local state optimistically
    const col = board.columns.find((c) => c.id === columnId);
    const removedCardIds = new Set(col?.cardIds ?? []);

    setBoard({
      ...board,
      columns: board.columns.filter((c) => c.id !== columnId),
      cards: Object.fromEntries(
        Object.entries(board.cards).filter(([id]) => !removedCardIds.has(id))
      ),
    });

    api.deleteColumn(columnId, boardId).catch((err) => {
      setBoard(prev);
      showError(err.message);
    });
  };

  const activeCard = activeCardId && board ? board.cards[activeCardId] : null;

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const isCardVisible = (card: Card): boolean => {
    if (filterPriority && (card.priority ?? "none") !== filterPriority) return false;
    if (filterOverdue) {
      if (!card.due_date) return false;
      const due = new Date(card.due_date + "T00:00:00");
      if (due >= today) return false;
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchTitle = card.title.toLowerCase().includes(q);
      const matchDetails = card.details.toLowerCase().includes(q);
      const matchLabels = (card.labels ?? []).some((l) => l.toLowerCase().includes(q));
      if (!matchTitle && !matchDetails && !matchLabels) return false;
    }
    return true;
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
          Loading board...
        </p>
      </div>
    );
  }

  if (!board) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm font-semibold text-red-600">
          Failed to load board.
        </p>
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative flex min-h-screen flex-col gap-5 px-5 pb-8 pt-5">
        <header className="flex flex-wrap items-center gap-3 rounded-2xl border border-[var(--stroke)] bg-white/80 px-5 py-3 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex items-center gap-3">
            <h1 className="font-display text-lg font-semibold text-[var(--navy-dark)]">
              Kanban Studio
            </h1>
            <div className="h-1 w-8 rounded-full bg-[var(--accent-yellow)]" />
          </div>
          <div className="mx-1 h-5 w-px bg-[var(--stroke)]" />
          {boards && boards.length > 0 && boardId && onBoardSelect && onBoardCreate && onBoardRename && onBoardDelete ? (
            <div className="flex-1">
              <BoardSelector
                boards={boards}
                currentBoardId={boardId}
                onSelect={onBoardSelect}
                onCreate={onBoardCreate}
                onRename={onBoardRename}
                onDelete={onBoardDelete}
                onShare={boardId ? () => setShowShare(true) : undefined}
              />
            </div>
          ) : (
            <div className="flex flex-1 flex-wrap items-center gap-2">
              {board.columns.map((column) => (
                <div
                  key={column.id}
                  className="flex items-center gap-1.5 rounded-full border border-[var(--stroke)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.15em] text-[var(--navy-dark)]"
                >
                  <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                  {column.title}
                </div>
              ))}
            </div>
          )}
          <div className="flex items-center gap-2 ml-auto shrink-0">
            {username && (
              <button
                onClick={() => setShowAccount(true)}
                className="rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-1.5 text-xs font-semibold text-[var(--navy-dark)] hover:border-[var(--primary-blue)] transition-colors"
                title="Account settings"
              >
                {username}
              </button>
            )}
            {onLogout && (
              <button
                onClick={onLogout}
                className="rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)] transition-colors hover:text-[var(--navy-dark)]"
              >
                Sign out
              </button>
            )}
          </div>
        </header>

        <div className="flex flex-wrap items-center gap-3 px-1">
          <input
            ref={searchInputRef}
            type="search"
            placeholder="Search cards... (/)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="rounded-xl border border-[var(--stroke)] bg-white px-3 py-1.5 text-xs text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)] w-44"
            aria-label="Search cards"
          />
          <span className="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)]">Filter:</span>
          {["none", "low", "medium", "high", "urgent"].map((p) => (
            <button
              key={p}
              onClick={() => setFilterPriority(filterPriority === p ? null : p)}
              className={`rounded-full border px-3 py-0.5 text-xs font-semibold transition-colors ${
                filterPriority === p
                  ? "border-[var(--primary-blue)] bg-[var(--primary-blue)] text-white"
                  : "border-[var(--stroke)] text-[var(--gray-text)] hover:border-[var(--primary-blue)]"
              }`}
            >
              {p}
            </button>
          ))}
          <button
            onClick={() => setFilterOverdue(!filterOverdue)}
            className={`rounded-full border px-3 py-0.5 text-xs font-semibold transition-colors ${
              filterOverdue
                ? "border-red-500 bg-red-500 text-white"
                : "border-[var(--stroke)] text-[var(--gray-text)] hover:border-red-500"
            }`}
          >
            overdue
          </button>
          {(filterPriority || filterOverdue || searchQuery) && (
            <button
              onClick={() => { setFilterPriority(null); setFilterOverdue(false); setSearchQuery(""); }}
              className="text-xs text-[var(--gray-text)] hover:text-[var(--navy-dark)] underline"
            >
              clear
            </button>
          )}
          <div className="ml-auto flex gap-2">
            <button
              onClick={() => setShowDashboard(true)}
              className="rounded-full border border-[var(--stroke)] px-3 py-0.5 text-xs text-[var(--gray-text)] hover:border-[var(--navy-dark)] transition-colors"
              title="My dashboard"
            >
              dashboard
            </button>
            {boardId && (
              <button
                onClick={() => setShowSprints(true)}
                className="rounded-full border border-[var(--stroke)] px-3 py-0.5 text-xs text-[var(--gray-text)] hover:border-[var(--navy-dark)] transition-colors"
                title="Sprints"
              >
                sprints
              </button>
            )}
            <button
              onClick={() => setShowArchive(true)}
              className="rounded-full border border-[var(--stroke)] px-3 py-0.5 text-xs text-[var(--gray-text)] hover:border-[var(--navy-dark)] transition-colors"
              title="View archived cards"
            >
              archive
            </button>
            {boardId && (
              <>
                <button
                  onClick={() => setShowStats(true)}
                  className="rounded-full border border-[var(--stroke)] px-3 py-0.5 text-xs text-[var(--gray-text)] hover:border-[var(--navy-dark)] transition-colors"
                  title="Board statistics"
                >
                  stats
                </button>
                <button
                  onClick={() => setShowActivity(true)}
                  className="rounded-full border border-[var(--stroke)] px-3 py-0.5 text-xs text-[var(--gray-text)] hover:border-[var(--navy-dark)] transition-colors"
                  title="View board activity"
                >
                  activity
                </button>
                <button
                  onClick={handleExport}
                  className="rounded-full border border-[var(--stroke)] px-3 py-0.5 text-xs text-[var(--gray-text)] hover:border-[var(--navy-dark)] transition-colors"
                  title="Export board as JSON"
                >
                  export
                </button>
              </>
            )}
          </div>
        </div>

        <DndContext
          sensors={sensors}
          collisionDetection={collisionDetection}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
        >
          <section className="overflow-x-auto">
            <div
              className="grid gap-4"
              style={{ gridTemplateColumns: `repeat(${board.columns.length + 1}, minmax(190px, 1fr))` }}
            >
              {board.columns.map((column, idx) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  cards={column.cardIds.map((id) => board.cards[id]).filter((c): c is Card => c !== undefined && isCardVisible(c))}
                  isHighlighted={overColumnId === column.id}
                  onRename={handleRenameColumn}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                  onArchiveCard={handleArchiveCard}
                  onEditCard={handleEditCard}
                  boardId={boardId}
                  onDeleteColumn={handleDeleteColumn}
                  onUpdatePriority={handleUpdatePriority}
                  onUpdateDueDate={handleUpdateDueDate}
                  onUpdateLabels={handleUpdateLabels}
                  onSetWipLimit={handleSetWipLimit}
                  onChecklistCountChange={handleChecklistCountChange}
                  onCommentCountChange={handleCommentCountChange}
                  onAssign={handleAssign}
                  boardMembers={boardMembers}
                  onBulkArchive={boardId ? handleBulkArchive : undefined}
                  onOpenCardDetail={(cardId) => setDetailCardId(cardId)}
                  onRegisterAddTrigger={idx === 0 ? (fn) => { firstAddCardRef.current = fn; } : undefined}
                />
              ))}
              {/* Add column slot */}
              <div className="flex flex-col gap-3 rounded-2xl border border-dashed border-[var(--stroke)] bg-white/40 p-4">
                {addingColumn ? (
                  <div className="flex flex-col gap-2">
                    <input
                      autoFocus
                      placeholder="Column name"
                      value={newColumnTitle}
                      onChange={(e) => setNewColumnTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleAddColumn();
                        if (e.key === "Escape") {
                          setAddingColumn(false);
                          setNewColumnTitle("");
                        }
                      }}
                      className="rounded-xl border border-[var(--primary-blue)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={handleAddColumn}
                        className="flex-1 rounded-xl bg-[var(--primary-blue)] py-1.5 text-xs font-semibold text-white"
                      >
                        Add
                      </button>
                      <button
                        onClick={() => {
                          setAddingColumn(false);
                          setNewColumnTitle("");
                        }}
                        className="flex-1 rounded-xl border border-[var(--stroke)] py-1.5 text-xs font-semibold text-[var(--gray-text)]"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setAddingColumn(true)}
                    className="flex h-full min-h-[60px] items-center justify-center rounded-xl text-sm font-semibold text-[var(--gray-text)] hover:text-[var(--primary-blue)] transition-colors"
                  >
                    + Add Column
                  </button>
                )}
              </div>
            </div>
          </section>
          <DragOverlay>
            {activeCard ? (
              <div className="w-[260px]">
                <KanbanCardPreview card={activeCard} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>

        {error && (
          <div
            role="alert"
            className="fixed bottom-6 left-1/2 -translate-x-1/2 rounded-xl border border-red-200 bg-red-50 px-5 py-3 text-sm font-medium text-red-700 shadow-lg"
          >
            {error}
          </div>
        )}
      </main>
      {showAccount && username && (
        <AccountModal username={username} onClose={() => setShowAccount(false)} />
      )}
      {showArchive && (
        <ArchivePanel
          boardId={boardId}
          onRestore={() => { /* board reloads on next fetch */ }}
          onClose={() => setShowArchive(false)}
        />
      )}
      {showStats && boardId && (
        <StatsPanel boardId={boardId} onClose={() => setShowStats(false)} />
      )}
      {showShare && boardId && (
        <BoardSharePanel
          boardId={boardId}
          onClose={() => setShowShare(false)}
          onMembersChanged={() => {
            if (boardId) api.getBoardMembers(boardId).then(setBoardMembers).catch(() => {});
          }}
        />
      )}
      {showDashboard && (
        <DashboardPanel
          onClose={() => setShowDashboard(false)}
          onNavigateBoard={(bid) => {
            onBoardSelect?.(bid);
            setShowDashboard(false);
          }}
        />
      )}
      {showSprints && boardId && (
        <SprintPanel boardId={boardId} onClose={() => setShowSprints(false)} />
      )}
      {showActivity && boardId && (
        <ActivityFeed boardId={boardId} onClose={() => setShowActivity(false)} />
      )}
      {detailCardId && board?.cards[detailCardId] && (() => {
        const card = board.cards[detailCardId];
        const col = board.columns.find((c) => c.cardIds.includes(detailCardId));
        return (
          <CardDetailModal
            card={card}
            columnTitle={col?.title ?? ""}
            boardId={boardId}
            boardMembers={boardMembers}
            allCardTitles={board ? Object.fromEntries(Object.values(board.cards).map((c) => [c.id, c.title])) : undefined}
            onClose={() => setDetailCardId(null)}
            onEdit={handleEditCard}
            onUpdatePriority={handleUpdatePriority}
            onUpdateDueDate={handleUpdateDueDate}
            onUpdateLabels={handleUpdateLabels}
            onAssign={handleAssign}
            onChecklistCountChange={handleChecklistCountChange}
            onCommentCountChange={handleCommentCountChange}
            onArchive={(cardId) => { handleArchiveCard(col?.id ?? "", cardId); setDetailCardId(null); }}
            onDuplicate={handleDuplicateCard}
          />
        );
      })()}
    </div>
  );
};
