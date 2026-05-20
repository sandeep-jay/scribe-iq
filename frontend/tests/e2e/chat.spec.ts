import { expect, test } from "@playwright/test";

test("chat page renders deferred retrieval banner", async ({ page }) => {
  await page.goto("/chat");
  await expect(page.getByRole("heading", { name: "Chat-on-corpus" })).toBeVisible();
  await expect(page.getByText("RAG chat requires seeded embeddings")).toBeVisible();
});
