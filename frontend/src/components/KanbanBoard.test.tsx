import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData } from "@/test/fixtures";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  fetchBoard: vi.fn(),
  saveBoard: vi.fn(),
  createCard: vi.fn(),
  deleteCard: vi.fn(),
  archiveCard: vi.fn(),
  updateCard: vi.fn(),
  renameColumn: vi.fn(),
  saveColumnsOrder: vi.fn(),
  addColumn: vi.fn(),
  deleteColumn: vi.fn(),
  setAuthErrorHandler: vi.fn(),
}));

const renderBoard = () =>
  render(<KanbanBoard initialBoard={initialData} />);

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];

beforeEach(() => {
  vi.mocked(api.renameColumn).mockResolvedValue(undefined);
  vi.mocked(api.saveColumnsOrder).mockResolvedValue(initialData);
});

describe("KanbanBoard", () => {
  it("renders five columns", () => {
    renderBoard();
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column on blur", async () => {
    renderBoard();
    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    await userEvent.tab(); // blur to commit
    await waitFor(() =>
      expect(api.renameColumn).toHaveBeenCalledWith("col-backlog", "New Name", undefined)
    );
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    vi.mocked(api.createCard).mockResolvedValueOnce({
      id: "card-new",
      title: "New card",
      details: "Notes",
    });
    vi.mocked(api.archiveCard).mockResolvedValueOnce(undefined);

    renderBoard();
    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    await waitFor(() =>
      expect(within(column).getByText("New card")).toBeInTheDocument()
    );

    const archiveButton = within(column).getByRole("button", {
      name: /archive new card/i,
    });
    await userEvent.click(archiveButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("edits a card title inline", async () => {
    vi.mocked(api.updateCard).mockResolvedValueOnce(undefined);

    renderBoard();
    const column = getFirstColumn();
    const title = within(column).getByText("Align roadmap themes");
    await userEvent.click(title);

    const input = within(column).getByLabelText("Edit card title");
    await userEvent.clear(input);
    await userEvent.type(input, "Updated title{enter}");

    expect(within(column).getByText("Updated title")).toBeInTheDocument();
    expect(within(column).queryByText("Align roadmap themes")).not.toBeInTheDocument();
  });

  it("edits card details inline", async () => {
    vi.mocked(api.updateCard).mockResolvedValueOnce(undefined);

    renderBoard();
    const column = getFirstColumn();
    const details = within(column).getByText(
      "Draft quarterly themes with impact statements and metrics."
    );
    await userEvent.click(details);

    const textarea = within(column).getByLabelText("Edit card details");
    await userEvent.clear(textarea);
    await userEvent.type(textarea, "New details");
    // blur to commit
    await userEvent.tab();

    expect(within(column).getByText("New details")).toBeInTheDocument();
  });

  it("shows loading state when no initialBoard", () => {
    vi.mocked(api.fetchBoard).mockReturnValue(new Promise(() => {})); // never resolves
    render(<KanbanBoard />);
    expect(screen.getByText("Loading board...")).toBeInTheDocument();
  });

  it("reverts card delete when API fails", async () => {
    vi.mocked(api.archiveCard).mockRejectedValueOnce(new Error("Server error"));
    renderBoard();
    const column = getFirstColumn();

    expect(within(column).getByText("Align roadmap themes")).toBeInTheDocument();

    const archiveBtn = within(column).getByRole("button", {
      name: /archive align roadmap themes/i,
    });
    await userEvent.click(archiveBtn);

    // Optimistic delete removes the card, API failure restores it
    await waitFor(() =>
      expect(within(column).getByText("Align roadmap themes")).toBeInTheDocument()
    );
  });

  it("reverts card edit when API fails", async () => {
    vi.mocked(api.updateCard).mockRejectedValueOnce(new Error("Server error"));
    renderBoard();
    const column = getFirstColumn();

    await userEvent.click(within(column).getByText("Align roadmap themes"));
    const input = within(column).getByLabelText("Edit card title");
    await userEvent.clear(input);
    await userEvent.type(input, "Changed title{enter}");

    // Optimistic update shows new title, API failure reverts it
    await waitFor(() =>
      expect(within(column).getByText("Align roadmap themes")).toBeInTheDocument()
    );
  });

  it("reverts column rename when API fails", async () => {
    vi.mocked(api.renameColumn).mockRejectedValueOnce(new Error("Server error"));
    renderBoard();
    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");

    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    await userEvent.tab(); // blur to commit

    // Optimistic rename applies, API failure reverts to original title
    await waitFor(() => expect(input).toHaveValue("Backlog"));
  });
});
