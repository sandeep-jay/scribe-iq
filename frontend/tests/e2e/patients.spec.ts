import { expect, test } from "@playwright/test";

test("patients route renders heading", async ({ page }) => {
  await page.goto("/patients");
  await expect(page.getByRole("heading", { name: "Patients" })).toBeVisible();
});

test("patient detail fallback renders heading", async ({ page }) => {
  await page.goto("/patients/non-existent-patient");
  await expect(page.getByRole("heading", { name: "Patient detail" })).toBeVisible();
});
