import { expect, test } from "@playwright/test";

test("the counter page counts a click", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button").click();
  await expect(page.getByRole("button")).toHaveText("1");
});
