import { test, expect } from "@playwright/test";
import { existsSync, unlinkSync } from "node:fs";
// Database isolated from the developer's interactive workbench.
// Each CI run starts in a clean checkout; remove only this named test database before launch via test script.
test("primary workflow and audit evidence", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  const capture = async () => {
    await page.setViewportSize({width:390,height:844});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
    await page.setViewportSize({width:1440,height:1000});
    await page.evaluate(()=>window.scrollTo(0,0));
    if (process.env.UPDATE_SCREENSHOTS === "1")
      await page.screenshot({ path: "../docs/screenshot.png", fullPage: true });
  };
  await page.getByRole("button", { name: "运行可复现实验" }).click();
  await expect(page.getByText("逐样本追踪")).toBeVisible();
  await capture();
  await page.getByLabel("被测目标").selectOption("keyword");
  await page.getByRole("button", { name: "运行可复现实验" }).click();
  await expect(page.getByLabel("选择历史基线").locator("option")).toHaveCount(
    2,
  );
  await page.getByLabel("选择历史基线").selectOption({ index: 1 });
  await page.getByRole("button", { name: "与当前运行比较" }).click();
  await expect(page.getByText(/改善 .* 项 · 回归/)).toBeVisible();
  await page.getByRole("button", { name: "审计证据" }).click();
  await expect(page.getByText("VALID", { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});
test("mobile layout remains within viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await expect(page.locator("h1")).toBeVisible();
});
