import { expect, test } from "@playwright/test";

import { login, USERS } from "./helpers";

test.describe("Финансы: приход с подтверждением (ФНС-01)", () => {
  test("бухгалтер добавляет приход → pending; главбух подтверждает", async ({ page }) => {
    await login(page, USERS.accountant);
    await page.goto("/finance");

    // Добавить приход на уникальную сумму.
    await page.getByRole("button", { name: "Добавить приход" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByLabel("Бизнес").selectOption({ index: 1 });
    await dialog.getByLabel("Сумма").fill("98765.43");
    await dialog.getByRole("button", { name: /Создать|Сохранить|Добавить/ }).click();
    await expect(dialog).not.toBeVisible({ timeout: 10_000 });

    // Он в статусе «Ожидает».
    const row = page.locator("tbody tr", { hasText: "98 765,43" }).first();
    await expect(row).toBeVisible();
    await expect(row.getByText("Ожидает")).toBeVisible();

    // Подтверждение главбухом.
    await login(page, USERS.chief);
    await page.goto("/finance");
    const pendingRow = page.locator("tbody tr", { hasText: "98 765,43" }).first();
    await expect(pendingRow).toBeVisible();
    const confirmBtn = pendingRow.getByRole("button", { name: "Подтвердить приход" });
    await expect(confirmBtn).toBeVisible(); // icon-кнопка с aria-label
    await confirmBtn.click();
    await expect(
      page.locator("tbody tr", { hasText: "98 765,43" }).first().getByText("Подтверждено"),
    ).toBeVisible({ timeout: 10_000 });
  });

  test("владелец видит финансы без кнопок создания; кассиру раздел недоступен", async ({ page }) => {
    await login(page, USERS.owner);
    await page.goto("/finance");
    await expect(page.locator(".tbl tbody tr").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Добавить приход" })).toHaveCount(0);

    await login(page, USERS.cashierStroy);
    await page.goto("/finance");
    await expect(page.getByText("Недостаточно прав")).toBeVisible();
  });

  test("прибыль по бизнесам (ФНС-04) заполнена", async ({ page }) => {
    await login(page, USERS.chief);
    await page.goto("/finance");
    await expect(page.locator(".kpi-grid .card").first()).toBeVisible();
    await expect(page.locator(".kpi-grid").getByText(/с\./).first()).toBeVisible();
  });
});
