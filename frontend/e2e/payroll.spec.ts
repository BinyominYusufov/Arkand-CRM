import { expect, test } from "@playwright/test";

import { login, USERS } from "./helpers";

test.describe("Зарплата: расчёт за период (ЗРП-01…05)", () => {
  test("запуск расчёта → таблица base/bonus/total с разбивкой", async ({ page }) => {
    await login(page, USERS.chief);
    await page.goto("/payroll");

    await page.getByRole("button", { name: "Запустить расчёт зарплаты" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    // Дефолт — текущий период (черновик пересчитывается идемпотентно).
    await dialog.getByRole("button", { name: /Запустить|Создать|Сохранить/ }).click();
    await expect(dialog).not.toBeVisible({ timeout: 15_000 });

    // Таблица строк расчёта: сотрудники с окладом/бонусом/итогом.
    await expect(page.getByText("Парвина Саидова")).toBeVisible({ timeout: 10_000 });
    const salesRow = page.locator("tr", { hasText: "Хуршед Насимов" });
    await expect(salesRow).toBeVisible();
    // Разбивка раскрывается и показывает как посчитано.
    await salesRow.getByRole("button").first().click();
    await expect(page.getByText(/per_unit_tiered|marginal|Разбивка/i).first()).toBeVisible();
  });

  test("список расчётов: утверждённые месяцы + черновик", async ({ page }) => {
    await login(page, USERS.chief);
    await page.goto("/payroll");
    await expect(page.getByText("Утверждён").first()).toBeVisible();
    await expect(page.getByText("Черновик").first()).toBeVisible();
  });

  test("кассиру раздел недоступен", async ({ page }) => {
    await login(page, USERS.cashierStroy);
    await page.goto("/payroll");
    await expect(page.getByText("Недостаточно прав")).toBeVisible();
  });
});
