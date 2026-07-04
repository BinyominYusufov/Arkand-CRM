import { expect, test } from "@playwright/test";

import { login, PASSWORD, USERS } from "./helpers";

test.describe("Локализация ru ↔ tj", () => {
  test("переключение языка меняет интерфейс", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("button", { name: "Войти" })).toBeVisible();

    // Переключаем на таджикский.
    await page.getByRole("button", { name: "TJ" }).click();
    await expect(page.getByRole("button", { name: "Ворид шудан" })).toBeVisible();

    // Входим на таджикском — сайдбар на tj.
    await page.getByLabel("Почта").fill(USERS.chief);
    await page.getByLabel("Парол", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Ворид шудан" }).click();
    await expect(page.getByRole("link", { name: "Молия" })).toBeVisible({ timeout: 15_000 });

    // Обратно на русский.
    await page.getByRole("button", { name: "RU" }).click();
    await expect(page.getByRole("link", { name: "Финансы" })).toBeVisible();
  });

  test("icon-кнопки имеют доступные подписи (aria-label)", async ({ page }) => {
    await login(page, USERS.chief);
    await page.goto("/finance");
    await expect(page.locator(".tbl tbody tr").first()).toBeVisible();
    // Все icon-кнопки в таблице обязаны иметь aria-label.
    const unnamed = await page
      .locator(".tbl .icon-btn:not([aria-label])")
      .count();
    expect(unnamed).toBe(0);
    // Сайдбар: кнопки сворачивания и выхода подписаны.
    await expect(page.getByRole("button", { name: "Выйти" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Свернуть меню" })).toBeVisible();
  });
});
