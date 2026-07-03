import { expect, test } from "@playwright/test";

import { login, USERS } from "./helpers";

test.describe("Кассы: изоляция и лимит (КАС-02…04)", () => {
  test("кассир видит только свою кассу", async ({ page }) => {
    await login(page, USERS.cashierBuro);
    await expect(page).toHaveURL(/\/cash/);
    await expect(
      page.locator(".card__title", { hasText: "Касса Проект-Бюро" }),
    ).toBeVisible();
    await expect(page.getByText("Касса Строй-Инвест")).toHaveCount(0);
    await expect(page.getByText("Операторская касса")).toHaveCount(0);
  });

  test("операция в пределах лимита проходит, сверх лимита — ошибка", async ({ page }) => {
    await login(page, USERS.cashierBuro);
    await page.goto("/cash");

    // Небольшая операция — успех.
    await page.getByRole("button", { name: "Добавить операцию" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Касса").selectOption({ index: 1 });
    await dialog.getByLabel("Сумма").fill("150");
    await dialog.getByRole("button", { name: /Создать|Сохранить|Добавить/ }).click();
    await expect(dialog).not.toBeVisible({ timeout: 10_000 });

    // Операция, пробивающая лимит (касса ~88% от 40 000) — ошибка лимита.
    await page.getByRole("button", { name: "Добавить операцию" }).click();
    const dialog2 = page.getByRole("dialog");
    await dialog2.getByLabel("Касса").selectOption({ index: 1 });
    await dialog2.getByLabel("Сумма").fill("100000");
    await dialog2.getByRole("button", { name: /Создать|Сохранить|Добавить/ }).click();
    await expect(dialog2.getByRole("alert")).toContainText(/лимит/i, { timeout: 10_000 });
  });

  test("финотдел видит все кассы и превышение лимита (AlertTriangle)", async ({ page }) => {
    await login(page, USERS.chief);
    await page.goto("/cash");
    await expect(
      page.locator(".card__title", { hasText: "Касса Проект-Бюро" }),
    ).toBeVisible();
    await expect(
      page.locator(".card__title", { hasText: "Касса Строй-Инвест" }),
    ).toBeVisible();
    await expect(
      page.locator(".card__title", { hasText: "Операторская касса" }),
    ).toBeVisible();
    // Касса «Операторская» превышала лимит после его снижения.
    await expect(page.getByText("Лимит превышен").first()).toBeVisible();
  });
});
