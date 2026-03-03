import { expect, test, type Page } from "@playwright/test";

const MOCK_BOARD = {
  columns: [
    { id: "col-backlog", title: "Backlog", cardIds: ["card-1", "card-2"] },
    { id: "col-discovery", title: "Discovery", cardIds: [] },
    { id: "col-progress", title: "In Progress", cardIds: [] },
    { id: "col-review", title: "Review", cardIds: [] },
    { id: "col-done", title: "Done", cardIds: [] },
  ],
  cards: {
    "card-1": { id: "card-1", title: "Align roadmap themes", details: "Draft quarterly themes." },
    "card-2": { id: "card-2", title: "Gather customer signals", details: "Review support tags." },
  },
};

async function setupMocks(page: Page) {
  // Set auth token so the app skips the login page
  await page.addInitScript(() => {
    localStorage.setItem("token", "mock-jwt-token");
  });

  await page.route("/api/auth/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ username: "user" }),
    })
  );

  await page.route("/api/board", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_BOARD),
    })
  );

  await page.route("/api/board/cards", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ id: "card-new", title: "Playwright card", details: "Added via e2e." }),
    })
  );

  await page.route("/api/board/cards/**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "{}" })
  );

  await page.route("/api/board/columns/**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_BOARD),
    })
  );
}

test("loads the kanban board", async ({ page }) => {
  await setupMocks(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  await setupMocks(page);
  await page.goto("/");
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Playwright card");
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText("Playwright card")).toBeVisible();
});

test("moves a card between columns", async ({ page }) => {
  await setupMocks(page);
  await page.goto("/");
  const card = page.getByTestId("card-card-1");
  const targetColumn = page.getByTestId("column-col-review");
  const cardBox = await card.boundingBox();
  const columnBox = await targetColumn.boundingBox();
  if (!cardBox || !columnBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  await page.mouse.move(
    cardBox.x + cardBox.width / 2,
    cardBox.y + cardBox.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(
    columnBox.x + columnBox.width / 2,
    columnBox.y + 120,
    { steps: 12 }
  );
  await page.mouse.up();
  await expect(targetColumn.getByTestId("card-card-1")).toBeVisible();
});

test("shows the AI chat sidebar", async ({ page }) => {
  await setupMocks(page);
  await page.goto("/");
  await expect(page.getByPlaceholder("Ask the AI...")).toBeVisible();
  await expect(page.getByRole("button", { name: /send/i })).toBeVisible();
});

test("sends a chat message and displays AI response", async ({ page }) => {
  await setupMocks(page);
  await page.route("/api/ai/chat", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ message: "I can help with that!", board_update: null }),
    })
  );

  await page.goto("/");
  await page.getByPlaceholder("Ask the AI...").fill("What cards do I have?");
  await page.getByRole("button", { name: /send/i }).click();

  await expect(page.getByText("What cards do I have?")).toBeVisible();
  await expect(page.getByText("I can help with that!")).toBeVisible();
});

test("AI board_update triggers board refresh", async ({ page }) => {
  await setupMocks(page);

  // Override /api/board to count GET calls (registered after setupMocks, takes precedence)
  let boardFetchCount = 0;
  await page.route("/api/board", (route) => {
    if (route.request().method() === "GET") boardFetchCount++;
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_BOARD),
    });
  });

  await page.route("/api/ai/chat", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        message: "Done, I added a card for you.",
        board_update: { ...MOCK_BOARD },
      }),
    })
  );

  await page.goto("/");
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
  const countAfterLoad = boardFetchCount;

  await page.getByPlaceholder("Ask the AI...").fill("Add a card");
  await page.getByRole("button", { name: /send/i }).click();

  await expect(page.getByText("Done, I added a card for you.")).toBeVisible();
  await expect.poll(() => boardFetchCount).toBeGreaterThan(countAfterLoad);
});
