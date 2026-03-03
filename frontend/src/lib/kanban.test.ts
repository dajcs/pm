import { moveCard, type Column } from "@/lib/kanban";

describe("moveCard", () => {
  const baseColumns: Column[] = [
    { id: "col-a", title: "A", cardIds: ["card-1", "card-2"] },
    { id: "col-b", title: "B", cardIds: ["card-3"] },
  ];

  it("reorders cards in the same column", () => {
    const result = moveCard(baseColumns, "card-2", "card-1");
    expect(result[0].cardIds).toEqual(["card-2", "card-1"]);
  });

  it("moves cards to another column", () => {
    const result = moveCard(baseColumns, "card-2", "card-3");
    expect(result[0].cardIds).toEqual(["card-1"]);
    expect(result[1].cardIds).toEqual(["card-2", "card-3"]);
  });

  it("drops cards to the end of a column", () => {
    const result = moveCard(baseColumns, "card-1", "col-b");
    expect(result[0].cardIds).toEqual(["card-2"]);
    expect(result[1].cardIds).toEqual(["card-3", "card-1"]);
  });

  it("returns columns unchanged when active equals over (same position no-op)", () => {
    const result = moveCard(baseColumns, "card-1", "card-1");
    // moveCard doesn't short-circuit on same id — the drag handler does. Within
    // the same column, oldIndex === newIndex so columns are returned unchanged.
    expect(result[0].cardIds).toEqual(["card-1", "card-2"]);
    expect(result[1].cardIds).toEqual(["card-3"]);
  });

  it("moves the only card out of a column leaving it empty", () => {
    const result = moveCard(baseColumns, "card-3", "col-a");
    expect(result[0].cardIds).toEqual(["card-1", "card-2", "card-3"]);
    expect(result[1].cardIds).toEqual([]);
  });

  it("moves a card into an empty column via column ID", () => {
    const cols: Column[] = [
      { id: "col-a", title: "A", cardIds: ["card-1"] },
      { id: "col-empty", title: "Empty", cardIds: [] },
    ];
    const result = moveCard(cols, "card-1", "col-empty");
    expect(result[0].cardIds).toEqual([]);
    expect(result[1].cardIds).toEqual(["card-1"]);
  });

  it("returns unchanged columns when active id is not found", () => {
    const result = moveCard(baseColumns, "card-ghost", "col-b");
    expect(result).toEqual(baseColumns);
  });
});
