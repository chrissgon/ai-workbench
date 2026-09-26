import { existsSync } from "node:fs";
import { expect, test } from "@playwright/test";

test("the generated site has a 404 page", () => {
  expect(existsSync(".output/public/404.html")).toBe(true);
});

test("the home page shows its title", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Example docs");
});
