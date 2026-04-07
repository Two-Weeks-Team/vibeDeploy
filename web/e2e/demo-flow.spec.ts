import { test, expect } from "@playwright/test";

test.describe("Demo Flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/demo");
  });

  test("/demo page auto-types YouTube URL", async ({ page }) => {
    // The demo page auto-types a YouTube URL into an input field.
    // Wait for the URL to appear in an input element.
    const urlInput = page.locator("input[type='text'], input[type='url'], input[placeholder]").first();

    // The demo types character-by-character, so wait for the full URL or enough of it
    await expect(urlInput).toHaveValue(/youtube\.com/, { timeout: 15_000 });
  });

  test("kanban board appears after transition", async ({ page }) => {
    // After the demo auto-types and clicks "start", the stage transitions to dashboard
    // which shows the kanban board. This takes a few seconds for the auto-animation.
    // The kanban board containers have specific column headings.

    // Wait for the demo transition to complete (auto-type + auto-click ~ 3-5s)
    const boardElement = page
      .getByText(/Analyzing|GO Ready|Building|Deployed|No-Go/i)
      .first();
    await expect(boardElement).toBeVisible({ timeout: 30_000 });
  });

  test("cards appear in the board", async ({ page }) => {
    // After the kanban board appears, demo timeline cards start populating.
    // The first card appears at ~6500ms (DEMO_SPEED_MULTIPLIER = 8, but raw timer is 6500ms).

    // Wait for at least one card title to appear in the board
    const cardTitle = page
      .getByText(/NutriPlan|SpendSense|StudyMate/i)
      .first();
    await expect(cardTitle).toBeVisible({ timeout: 45_000 });
  });

  test("session shows completed status at the end", async ({ page }) => {
    // The demo timeline fires a "completed" session status event.
    // This is signaled by the status bar or a completion indicator.
    // The longest timeline event is around 200 seconds raw time.
    // For a reasonable E2E timeout, we check for the completed state.

    test.slow(); // Mark as slow test — the demo timeline takes extended time

    // Wait for the completed status indicator
    const completedIndicator = page
      .getByText(/completed|session complete/i)
      .first();
    await expect(completedIndicator).toBeVisible({ timeout: 300_000 });
  });
});
