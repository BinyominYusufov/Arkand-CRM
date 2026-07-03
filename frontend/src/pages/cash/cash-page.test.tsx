import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import type { CashOperation, CashRegister } from "@/entities/cash-register";
import { formatMoney } from "@/shared/lib/money";
import { renderWithProviders } from "@/shared/test/render";
import { server } from "@/shared/test/msw";

import { CashPage } from "./index";

/** RTL нормализует NBSP из Intl.NumberFormat в обычный пробел. */
const norm = (s: string) => s.replace(/\s+/g, " ");

const registersFixture: CashRegister[] = [
  {
    id: 1,
    name: "Основная",
    business: 1,
    business_name: "Кафе Восток",
    turnover_limit: "50000.00",
    is_active: true,
    balance: "12500.00",
    month_turnover: "30000.00",
    limit_utilization: 60,
    over_limit: false,
    members: [1],
  },
  {
    id: 2,
    name: "Склад",
    business: 2,
    business_name: "Стройбаза",
    turnover_limit: "20000.00",
    is_active: true,
    balance: "21000.00",
    month_turnover: "25000.00",
    limit_utilization: 125,
    over_limit: true,
    members: [2],
  },
];

const operationsFixture: CashOperation[] = [
  {
    id: 10,
    register: 1,
    register_name: "Основная",
    business_name: "Кафе Восток",
    direction: "in",
    method: "cash",
    amount: "1500.00",
    note: "",
    created_by: 5,
    created_by_name: "Алишер Рахимов",
    occurred_at: "2026-07-01T10:30:00Z",
    created_at: "2026-07-01T10:30:00Z",
  },
  {
    id: 11,
    register: 2,
    register_name: "Склад",
    business_name: "Стройбаза",
    direction: "out",
    method: "transfer",
    amount: "700.00",
    note: "",
    created_by: 6,
    created_by_name: "Мадина Каримова",
    occurred_at: "2026-07-02T14:00:00Z",
    created_at: "2026-07-02T14:00:00Z",
  },
];

function mockApi() {
  const requests: string[] = [];
  server.use(
    http.get("/api/v1/cash/registers/", () =>
      HttpResponse.json(registersFixture),
    ),
    http.get("/api/v1/cash/operations/", ({ request }) => {
      requests.push(request.url);
      return HttpResponse.json({
        count: operationsFixture.length,
        next: null,
        previous: null,
        results: operationsFixture,
      });
    }),
  );
  return requests;
}

describe("CashPage", () => {
  it("рендерит карточки касс и таблицу операций из API", async () => {
    mockApi();
    renderWithProviders(<CashPage />);

    const card1 = await screen.findByTestId("cash-card-1");
    expect(
      within(card1).getByText("Основная · Кафе Восток"),
    ).toBeInTheDocument();
    const card2 = screen.getByTestId("cash-card-2");
    expect(within(card2).getByText("Склад · Стройбаза")).toBeInTheDocument();
    expect(within(card2).getByText("Лимит превышен")).toBeInTheDocument();
    expect(within(card1).queryByText("Лимит превышен")).not.toBeInTheDocument();

    expect(await screen.findByText("Алишер Рахимов")).toBeInTheDocument();
    expect(screen.getByText("Мадина Каримова")).toBeInTheDocument();
    expect(
      screen.getByText(norm(formatMoney("1500.00", { sign: "in" }))),
    ).toBeInTheDocument();
    expect(
      screen.getByText(norm(formatMoney("700.00", { sign: "out" }))),
    ).toBeInTheDocument();
  });

  it("фильтрует операции по направлению и кассе", async () => {
    const requests = mockApi();
    const user = userEvent.setup();
    renderWithProviders(<CashPage />);
    await screen.findByText("Алишер Рахимов");

    await user.selectOptions(screen.getByLabelText("Направление"), "out");
    await waitFor(() =>
      expect(requests.some((url) => url.includes("direction=out"))).toBe(true),
    );

    await user.selectOptions(screen.getByLabelText("Касса"), "2");
    await waitFor(() =>
      expect(
        requests.some(
          (url) => url.includes("register=2") && url.includes("direction=out"),
        ),
      ).toBe(true),
    );
  });

  it("показывает ошибку API по операциям", async () => {
    server.use(
      http.get("/api/v1/cash/registers/", () =>
        HttpResponse.json(registersFixture),
      ),
      http.get("/api/v1/cash/operations/", () =>
        HttpResponse.json(
          { code: "error", message: "Внутренняя ошибка" },
          { status: 500 },
        ),
      ),
    );
    renderWithProviders(<CashPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Внутренняя ошибка",
    );
  });
});
