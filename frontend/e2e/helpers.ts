import { expect, type Page } from "@playwright/test";

export const PASSWORD = "arkand2026";

export const USERS = {
  chief: "nigina@arkand.tj",
  accountant: "firuz@arkand.tj",
  cashierStroy: "jamshed@arkand.tj",
  cashierBuro: "farrukh@arkand.tj",
  owner: "owner@arkand.tj",
} as const;

/** Вход через UI; ждёт ухода со страницы логина. */
export async function login(page: Page, email: string) {
  // Гард уводит залогиненного с /login — сбрасываем предыдущую сессию.
  await page.goto("/login");
  await page.evaluate(() => localStorage.clear());
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  // exact: рядом с полем есть кнопка «Показать пароль», совпадающая по подстроке.
  await page.getByLabel("Пароль", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page).not.toHaveURL(/\/login/, { timeout: 15_000 });
}

export async function logoutViaUi(page: Page) {
  await page.getByRole("button", { name: "Выйти" }).click();
  await page.waitForURL(/\/login/);
}
