import { test, expect } from "@playwright/test";

test.describe("Navigation", () => {
  test("landing page loads and shows vibeDeploy title", async ({ page }) => {
    await page.goto("/");

    // The page title should contain vibeDeploy
    await expect(page).toHaveTitle(/vibeDeploy/);

    // The landing page renders the brand name in the heading
    const heading = page.getByText("vibeDeploy", { exact: false });
    await expect(heading.first()).toBeVisible();
  });

  test("Watch Demo button is visible and links to /demo", async ({ page }) => {
    await page.goto("/");

    const watchDemoLink = page.getByRole("link", { name: /Watch Demo/i });
    await expect(watchDemoLink).toBeVisible();
    await expect(watchDemoLink).toHaveAttribute("href", /\/demo/);
  });

  test("demo page loads and shows demo workspace", async ({ page }) => {
    await page.goto("/demo");

    // The demo page should display the landing stage first with the vibeDeploy brand
    const brand = page.getByText("vibeDeploy", { exact: false });
    await expect(brand.first()).toBeVisible();
  });

  test("dashboard page loads and shows System Dashboard", async ({ page }) => {
    await page.goto("/dashboard");

    // Wait for the System Dashboard heading to appear
    const heading = page.getByText("System Dashboard", { exact: false });
    await expect(heading.first()).toBeVisible({ timeout: 15_000 });
  });

  test("navigation between pages works", async ({ page }) => {
    // Start at landing page
    await page.goto("/");
    await expect(page).toHaveTitle(/vibeDeploy/);

    // Navigate to demo
    await page.goto("/demo");
    await expect(page.getByText("vibeDeploy", { exact: false }).first()).toBeVisible();

    // Navigate to dashboard
    await page.goto("/dashboard");
    await expect(
      page.getByText("System Dashboard", { exact: false }).first(),
    ).toBeVisible({ timeout: 15_000 });

    // Navigate back to landing
    await page.goto("/");
    await expect(page).toHaveTitle(/vibeDeploy/);
  });
});
