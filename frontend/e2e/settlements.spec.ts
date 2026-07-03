import { expect, test } from "@playwright/test";

import { login, USERS } from "./helpers";

test.describe("Взаиморасчёты: одобрение → авто-долг → закрытие (БАР-01…03, ХОЛ-32)", () => {
  test("одобрение передачи создаёт долг в реестре, долг закрывается", async ({ page }) => {
    await login(page, USERS.accountant);
    await page.goto("/settlements");

    // Таб «Передачи»: одобряем ожидающую передачу 6 000 (Проект-Бюро → Завод Алмосӣ).
    await page.getByRole("tab", { name: "Передачи" }).click();
    // Целимся в строку, у которой ЕСТЬ кнопка одобрения (не сводные строки).
    const row = page
      .locator("tbody tr", { hasText: "6 000,00" })
      .filter({ has: page.getByRole("button", { name: /Одобрить/ }) });
    await expect(row.first()).toBeVisible();
    await row.first().getByRole("button", { name: /Одобрить/ }).click();
    await expect(
      page
        .locator("tbody tr", { hasText: "6 000,00" })
        .filter({ hasText: "Одобрена" })
        .first(),
    ).toBeVisible({ timeout: 10_000 });

    // Реестр: появился долг «Завод Алмосӣ должен Проект-Бюро» на 6 000.
    await page.getByRole("tab", { name: "Реестр долгов" }).click();
    const debtRow = page
      .locator("tbody tr", { hasText: "6 000,00" })
      .filter({ has: page.getByRole("button", { name: "Закрыть долг" }) });
    await expect(debtRow.first()).toBeVisible();

    // Закрываем возвратом целиком.
    await debtRow.first().getByRole("button", { name: "Закрыть долг" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.locator("select").first().selectOption("return");
    await dialog.getByRole("button", { name: /Закрыть|Сохранить|Подтвердить/ }).click();
    await expect(dialog).not.toBeVisible({ timeout: 10_000 });
    await expect(
      page
        .locator("tbody tr", { hasText: "6 000,00" })
        .filter({ has: page.getByRole("button", { name: "Закрыть долг" }) }),
    ).toHaveCount(0);
  });

  test("ХОЛ-32: сверх порога одобряет только владелец", async ({ page }) => {
    await login(page, USERS.accountant);
    await page.goto("/settlements");
    await page.getByRole("tab", { name: "Передачи" }).click();

    // Передача 75 000 сверх порога 50 000.
    const bigRow = page.locator("tr", { hasText: "75 000,00" });
    await expect(bigRow.first()).toBeVisible();
    await bigRow.first().getByRole("button", { name: /Одобрить/ }).click();
    await expect(page.getByRole("alert")).toContainText(/владел/i, { timeout: 10_000 });

    // Владелец одобряет успешно.
    await login(page, USERS.owner);
    await page.goto("/settlements");
    await page.getByRole("tab", { name: "Передачи" }).click();
    const ownerRow = page.locator("tr", { hasText: "75 000,00" });
    await ownerRow.first().getByRole("button", { name: /Одобрить/ }).click();
    await expect(ownerRow.first().getByText("Одобрена")).toBeVisible({ timeout: 10_000 });
  });

  test("реестр долгов заполнен, есть просроченный долг", async ({ page }) => {
    await login(page, USERS.chief);
    await page.goto("/settlements");
    await expect(page.locator(".tbl tbody tr").first()).toBeVisible();
    await expect(page.getByText("Просрочен").first()).toBeVisible();
  });
});
