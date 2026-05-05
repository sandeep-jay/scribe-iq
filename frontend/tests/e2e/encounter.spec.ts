import { expect, test } from "@playwright/test";

test("encounter route renders graceful message for missing encounter", async ({ page }) => {
  await page.goto("/patients/unknown/encounters/unknown");
  await expect(page.getByText(/Could not reach the backend|Patient not found|No encounter keyed|Failed to fetch|fetch failed/i)).toBeVisible();
});
