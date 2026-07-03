import { expect, test } from "@playwright/test";

import { login, USERS } from "./helpers";

test.describe("Отчёты ФНС-10…13 и надстройка владельца (Часть 7)", () => {
  test("все отчёты заполнены, есть графики", async ({ page }) => {
    await login(page, USERS.chief);
    await page.goto("/reports");

    // ФНС-10: таблица по бизнесам + график.
    await expect(page.locator(".tbl tbody tr").first()).toBeVisible();
    await expect(page.getByText("Итого").first()).toBeVisible();
    await expect(page.locator("svg.recharts-surface").first()).toBeVisible();

    // ФНС-11: кассы с остатками; есть превышение лимита.
    await page.getByRole("tab", { name: /Кассы/ }).click();
    await expect(page.locator(".tbl tbody tr").first()).toBeVisible();
    await expect(page.getByText("Лимит превышен").first()).toBeVisible();

    // ФНС-12: долги.
    await page.getByRole("tab", { name: /Взаиморасчёты/ }).click();
    await expect(page.locator(".tbl tbody tr").first()).toBeVisible();

    // ФНС-13: зарплатный фонд.
    await page.getByRole("tab", { name: /Зарплат/ }).click();
    await expect(page.locator(".tbl tbody tr").first()).toBeVisible();
    await expect(page.getByText(/с\./).first()).toBeVisible();
  });

  test("владелец: KPI холдинга, график, экспорт JSON", async ({ page }) => {
    await login(page, USERS.owner);
    await page.goto("/overlay");

    await expect(page.locator(".kpi-grid .card")).toHaveCount(5);
    await expect(page.locator(".tbl tbody tr").first()).toBeVisible();
    await expect(page.locator("svg.recharts-surface").first()).toBeVisible();

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Экспорт консолидации" }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/arkand-overlay-v1\.json/);
  });

  test("overlay недоступен даже главбуху", async ({ page }) => {
    await login(page, USERS.chief);
    await page.goto("/overlay");
    await expect(page.getByText("Недостаточно прав")).toBeVisible();
  });
});
