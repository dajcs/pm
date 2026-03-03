/**
 * TST-3: Unit tests for KanbanBoard drag-end integration.
 * dnd-kit is fully mocked so we can fire DragEndEvents manually.
 */
import { act, render, screen, within } from "@testing-library/react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData } from "@/test/fixtures";
import * as api from "@/lib/api";
import type { DragEndEvent } from "@dnd-kit/core";

// Capture the onDragEnd callback registered by KanbanBoard
let capturedDragEnd: ((event: DragEndEvent) => void) | undefined;

vi.mock("@dnd-kit/core", async () => {
  const actual = await vi.importActual<typeof import("@dnd-kit/core")>("@dnd-kit/core");
  return {
    ...actual,
    DndContext: ({
      children,
      onDragEnd,
    }: {
      children: React.ReactNode;
      onDragEnd?: (e: DragEndEvent) => void;
      [key: string]: unknown;
    }) => {
      capturedDragEnd = onDragEnd;
      return <>{children}</>;
    },
    DragOverlay: ({ children }: { children?: React.ReactNode }) => (
      <>{children ?? null}</>
    ),
  };
});

vi.mock("@/lib/api", () => ({
  fetchBoard: vi.fn(),
  saveBoard: vi.fn(),
  createCard: vi.fn(),
  deleteCard: vi.fn(),
  updateCard: vi.fn(),
  renameColumn: vi.fn(),
  saveColumnsOrder: vi.fn(),
  setAuthErrorHandler: vi.fn(),
}));

function makeDragEndEvent(activeId: string, overId: string): DragEndEvent {
  return {
    active: { id: activeId, data: { current: undefined }, rect: { current: { translated: null, initial: null } } },
    over: { id: overId, data: { current: undefined }, rect: { current: { translated: null, initial: null }, disabled: false } },
    delta: { x: 0, y: 0 },
    activatorEvent: {} as PointerEvent,
    collisions: [],
  } as unknown as DragEndEvent;
}

beforeEach(() => {
  capturedDragEnd = undefined;
  vi.clearAllMocks();
  vi.mocked(api.saveColumnsOrder).mockResolvedValue(initialData);
  vi.mocked(api.renameColumn).mockResolvedValue(undefined);
});

describe("KanbanBoard drag-end", () => {
  it("moves a card to another column and calls saveColumnsOrder", async () => {
    render(<KanbanBoard initialBoard={initialData} />);

    // card-1 starts in col-backlog
    const backlog = screen.getByTestId("column-col-backlog");
    expect(within(backlog).getByText("Align roadmap themes")).toBeInTheDocument();

    // Fire drag end: move card-1 to col-discovery
    await act(async () => {
      capturedDragEnd?.(makeDragEndEvent("card-1", "col-discovery"));
    });

    const discovery = screen.getByTestId("column-col-discovery");
    expect(within(discovery).getByText("Align roadmap themes")).toBeInTheDocument();
    expect(within(backlog).queryByText("Align roadmap themes")).not.toBeInTheDocument();
    expect(api.saveColumnsOrder).toHaveBeenCalledTimes(1);
  });

  it("does nothing when active equals over (no-op drag)", async () => {
    render(<KanbanBoard initialBoard={initialData} />);

    await act(async () => {
      capturedDragEnd?.(makeDragEndEvent("card-1", "card-1"));
    });

    // Board unchanged
    const backlog = screen.getByTestId("column-col-backlog");
    expect(within(backlog).getByText("Align roadmap themes")).toBeInTheDocument();
    expect(api.saveColumnsOrder).not.toHaveBeenCalled();
  });

  it("reverts board state when saveColumnsOrder API call fails", async () => {
    vi.mocked(api.saveColumnsOrder).mockRejectedValueOnce(new Error("Network error"));
    render(<KanbanBoard initialBoard={initialData} />);

    await act(async () => {
      capturedDragEnd?.(makeDragEndEvent("card-1", "col-discovery"));
    });

    // Optimistic update moves card, then API fails and reverts
    await act(async () => {
      await Promise.resolve(); // flush microtasks
    });

    const backlog = screen.getByTestId("column-col-backlog");
    expect(within(backlog).getByText("Align roadmap themes")).toBeInTheDocument();
  });
});
