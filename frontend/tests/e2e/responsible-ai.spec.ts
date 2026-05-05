import { expect, test } from "@playwright/test";

test("responsible ai list page shows interactions shell", async ({ page }) => {
  await page.goto("/admin/responsible-ai");
  await expect(page.getByRole("heading", { name: "Responsible AI Control Center" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recent Interactions" })).toBeVisible();
});

test("responsible ai detail route loads detail shell", async ({ page }) => {
  await page.goto("/admin/responsible-ai/00000000-0000-0000-0000-000000000000");
  await expect(page.getByRole("heading", { name: "AI interaction detail" })).toBeVisible();
});
