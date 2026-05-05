import { expect, test } from "@playwright/test";

test("app boot renders home page", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Scribe|scribe/i);
});

test("responsible AI admin page loads shell", async ({ page }) => {
  await page.goto("/admin/responsible-ai");
  await expect(page.getByRole("heading", { name: "Responsible AI Control Center" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recent Interactions" })).toBeVisible();
});
