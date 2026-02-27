import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatSidebar, resetIdCounter } from "@/components/ChatSidebar";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  sendChatMessage: vi.fn(),
  fetchBoard: vi.fn(),
  saveBoard: vi.fn(),
  createCard: vi.fn(),
  deleteCard: vi.fn(),
  updateCard: vi.fn(),
  renameColumn: vi.fn(),
  saveColumnsOrder: vi.fn(),
  setAuthErrorHandler: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
  resetIdCounter();
});

describe("ChatSidebar", () => {
  it("renders the input and send button", () => {
    render(<ChatSidebar />);
    expect(screen.getByPlaceholderText("Ask the AI...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
  });

  it("sends a message and displays AI reply", async () => {
    vi.mocked(api.sendChatMessage).mockResolvedValueOnce({
      message: "Hello! I can help you manage your board.",
      board_update: null,
    });

    render(<ChatSidebar />);

    const input = screen.getByPlaceholderText("Ask the AI...");
    await userEvent.type(input, "Hello");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    // User message appears
    expect(screen.getByText("Hello")).toBeInTheDocument();

    // AI reply appears
    await waitFor(() =>
      expect(
        screen.getByText("Hello! I can help you manage your board.")
      ).toBeInTheDocument()
    );

    // Input is cleared
    expect(input).toHaveValue("");
  });

  it("calls onBoardUpdated when AI returns board_update", async () => {
    const onBoardUpdated = vi.fn();
    vi.mocked(api.sendChatMessage).mockResolvedValueOnce({
      message: "Done, card created.",
      board_update: { columns: [], cards: {} },
    });

    render(<ChatSidebar onBoardUpdated={onBoardUpdated} />);

    await userEvent.type(screen.getByPlaceholderText("Ask the AI..."), "Create a card");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => expect(onBoardUpdated).toHaveBeenCalledTimes(1));
  });

  it("editing a user message clears subsequent messages", async () => {
    // Send two messages to build history
    vi.mocked(api.sendChatMessage)
      .mockResolvedValueOnce({ message: "Reply 1", board_update: null })
      .mockResolvedValueOnce({ message: "Reply 2", board_update: null })
      .mockResolvedValueOnce({ message: "Reply to edit", board_update: null });

    render(<ChatSidebar />);
    const input = screen.getByPlaceholderText("Ask the AI...");

    // Send first message
    await userEvent.type(input, "First");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    await waitFor(() => expect(screen.getByText("Reply 1")).toBeInTheDocument());

    // Send second message
    await userEvent.type(input, "Second");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    await waitFor(() => expect(screen.getByText("Reply 2")).toBeInTheDocument());

    // Edit first user message -- click the Edit button
    const editButtons = screen.getAllByRole("button", { name: /^edit$/i });
    await userEvent.click(editButtons[0]);

    // Type new text in the textarea (not the main input)
    const textarea = screen.getByRole("textbox", { name: /edit message/i });
    await userEvent.clear(textarea);
    await userEvent.type(textarea, "Edited{enter}");

    // Subsequent messages (Second, Reply 1, Reply 2) should be gone
    await waitFor(() => {
      expect(screen.queryByText("Second")).not.toBeInTheDocument();
      expect(screen.queryByText("Reply 1")).not.toBeInTheDocument();
      expect(screen.queryByText("Reply 2")).not.toBeInTheDocument();
    });

    // New AI reply appears
    await waitFor(() =>
      expect(screen.getByText("Reply to edit")).toBeInTheDocument()
    );
  });

  it("deleting a user message removes it and subsequent messages", async () => {
    vi.mocked(api.sendChatMessage)
      .mockResolvedValueOnce({ message: "Reply 1", board_update: null })
      .mockResolvedValueOnce({ message: "Reply 2", board_update: null });

    render(<ChatSidebar />);
    const input = screen.getByPlaceholderText("Ask the AI...");

    // Send two messages
    await userEvent.type(input, "First");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    await waitFor(() => expect(screen.getByText("Reply 1")).toBeInTheDocument());

    await userEvent.type(input, "Second");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    await waitFor(() => expect(screen.getByText("Reply 2")).toBeInTheDocument());

    // Delete first user message
    const deleteButtons = screen.getAllByRole("button", { name: /^delete$/i });
    await userEvent.click(deleteButtons[0]);

    // All messages (First, Reply 1, Second, Reply 2) should be gone
    expect(screen.queryByText("First")).not.toBeInTheDocument();
    expect(screen.queryByText("Reply 1")).not.toBeInTheDocument();
    expect(screen.queryByText("Second")).not.toBeInTheDocument();
    expect(screen.queryByText("Reply 2")).not.toBeInTheDocument();
  });

  it("shows error message when API call fails", async () => {
    vi.mocked(api.sendChatMessage).mockRejectedValueOnce(new Error("Network error"));

    render(<ChatSidebar />);
    await userEvent.type(screen.getByPlaceholderText("Ask the AI..."), "Hello");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(
      () =>
        expect(
          screen.getByText("Sorry, something went wrong. Please try again.")
        ).toBeInTheDocument(),
      { timeout: 3000 }
    );
  });

  it("disables input and send while sending", async () => {
    // Make the API call hang indefinitely
    vi.mocked(api.sendChatMessage).mockReturnValue(new Promise(() => {}));

    render(<ChatSidebar />);
    const input = screen.getByPlaceholderText("Ask the AI...");
    await userEvent.type(input, "Hello");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    // Wait for the sending state to be reflected
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Ask the AI...")).toBeDisabled();
    });

    // Thinking indicator should show
    expect(screen.getByText("Thinking...")).toBeInTheDocument();
  });
});
