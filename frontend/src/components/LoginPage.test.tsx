import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginPage } from "@/components/LoginPage";

const mockOnLogin = vi.fn();

beforeEach(() => {
  mockOnLogin.mockReset();
  vi.restoreAllMocks();
});

describe("LoginPage", () => {
  it("renders the sign-in form", () => {
    render(<LoginPage onLogin={mockOnLogin} />);
    expect(screen.getByText("Kanban Studio")).toBeInTheDocument();
    expect(screen.getByText("Username")).toBeInTheDocument();
    expect(screen.getByText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("calls onLogin with token on successful login", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => ({ token: "test-jwt-token" }),
    } as Response);

    render(<LoginPage onLogin={mockOnLogin} />);
    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(mockOnLogin).toHaveBeenCalledWith("test-jwt-token"));
  });

  it("shows error on invalid credentials", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Invalid credentials" }),
    } as Response);

    render(<LoginPage onLogin={mockOnLogin} />);
    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Invalid username or password"));
    expect(mockOnLogin).not.toHaveBeenCalled();
  });

  it("shows error on network failure", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("Network error"));

    render(<LoginPage onLogin={mockOnLogin} />);
    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Unable to reach the server"));
    expect(mockOnLogin).not.toHaveBeenCalled();
  });
});
