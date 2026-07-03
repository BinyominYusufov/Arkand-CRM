import { expect, test } from "@playwright/test";

import { login, USERS } from "./helpers";

test.describe("Вход и видимость разделов по ролям", () => {
  test("неверный пароль — ошибка", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill(USERS.chief);
    await page.getByLabel("Пароль").fill("wrong-password");
    await page.getByRole("button", { name: "Войти" }).click();
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  });

  test("главбух: редирект в финансы, полный финотдел, без Холдинга", async ({ page }) => {
    await login(page, USERS.chief);
    await expect(page).toHaveURL(/\/finance/);
    const nav = page.getByRole("navigation", { name: "Main" });
    await expect(nav.getByRole("link", { name: "Финансы" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Кассы" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Взаиморасчёты" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Зарплата" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Отчёты" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Холдинг" })).toHaveCount(0);
  });

  test("кассир: видит только Кассы", async ({ page }) => {
    await login(page, USERS.cashierStroy);
    await expect(page).toHaveURL(/\/cash/);
    const nav = page.getByRole("navigation", { name: "Main" });
    await expect(nav.getByRole("link", { name: "Кассы" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Финансы" })).toHaveCount(0);
    await expect(nav.getByRole("link", { name: "Зарплата" })).toHaveCount(0);
  });

  test("владелец: видит Холдинг (Часть 7), финансы read-only", async ({ page }) => {
    await login(page, USERS.owner);
    const nav = page.getByRole("navigation", { name: "Main" });
    await expect(nav.getByRole("link", { name: "Холдинг" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Финансы" })).toBeVisible();
  });

  test("логотип ARKAND в сайдбаре и на входе; favicon подключён", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByAltText("ARKAND")).toBeVisible();
    await expect(page.locator('link[rel="icon"]')).toHaveAttribute(
      "href",
      /brand\/favicon\.svg/,
    );
    await login(page, USERS.chief);
    await expect(page.getByAltText("ARKAND")).toBeVisible();
  });
});
