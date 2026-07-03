import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { i18n } from "@/shared/lib/i18n";
import { formatMoney } from "@/shared/lib/money";
import { server } from "@/shared/test/msw";
import { renderWithProviders } from "@/shared/test/render";

import { ReportsPage } from "./index";

/* Testing-library нормализует NBSP в обычные пробелы — приводим ожидания к тому же виду. */
const normalizeSpaces = (s: string) => s.replace(/\s/g, " ");
const fm = (value: string, opts?: Parameters<typeof formatMoney>[1]) =>
  normalizeSpaces(formatMoney(value, opts));

/* Recharts ResponsiveContainer требует ResizeObserver, которого нет в jsdom. */
vi.stubGlobal(
  "ResizeObserver",
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  },
);

const businessesFixture = [
  { id: 1, name: "Мебель", code: "MEB", kind: "furniture", kind_display: "Мебель", is_active: true },
  { id: 2, name: "Кафе", code: "CAFE", kind: "cafe", kind_display: "Кафе", is_active: true },
];

const cashflowFixture = {
  businesses: [
    {
      business_id: 1,
      business_name: "Мебель",
      income: "50000.00",
      expense: "20000.00",
      profit: "30000.00",
    },
    {
      business_id: 2,
      business_name: "Кафе",
      income: "10000.00",
      expense: "4000.00",
      profit: "6000.00",
    },
  ],
  total: { income: "60000.00", expense: "24000.00", profit: "36000.00" },
};

const monthlyFixture = {
  months: 6,
  rows: [
    {
      month: "2026-01",
      business_id: 1,
      business_name: "Мебель",
      income: "1000.00",
      expense: "500.00",
    },
  ],
};

const categoriesFixture = {
  rows: [{ category_id: 1, category_name: "Материалы", total: "9000.00", count: 4 }],
};

function mockCashflowHandlers() {
  server.use(
    http.get("/api/v1/businesses/", () => HttpResponse.json(businessesFixture)),
    http.get("/api/v1/reports/cashflow", () => HttpResponse.json(cashflowFixture)),
    http.get("/api/v1/reports/cashflow/monthly", () => HttpResponse.json(monthlyFixture)),
    http.get("/api/v1/reports/expenses/by-category", () =>
      HttpResponse.json(categoriesFixture),
    ),
  );
}

describe("ReportsPage", () => {
  it("ФНС-10: таблица рендерит агрегаты по бизнесам и строку Итого", async () => {
    mockCashflowHandlers();
    renderWithProviders(<ReportsPage />);

    expect((await screen.findAllByText("Мебель")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Кафе").length).toBeGreaterThan(0);
    // приход со знаком "+", расход со знаком "−"
    expect(screen.getByText(fm("50000.00", { sign: "in" }))).toBeInTheDocument();
    expect(screen.getByText(fm("20000.00", { sign: "out" }))).toBeInTheDocument();
    expect(screen.getByText(fm("30000.00"))).toBeInTheDocument();
    // строка Итого
    expect(screen.getByText("Итого")).toBeInTheDocument();
    expect(screen.getByText(fm("60000.00", { sign: "in" }))).toBeInTheDocument();
    expect(screen.getByText(fm("24000.00", { sign: "out" }))).toBeInTheDocument();
    expect(screen.getByText(fm("36000.00"))).toBeInTheDocument();
  });

  it("ФНС-11: показывает badge при превышении лимита кассы", async () => {
    mockCashflowHandlers();
    server.use(
      http.get("/api/v1/reports/cash-registers", () =>
        HttpResponse.json({
          registers: [
            {
              id: 1,
              name: "Основная касса",
              business_id: 1,
              business_name: "Мебель",
              balance: "5000.00",
              month_turnover: "120000.00",
              turnover_limit: "100000.00",
              limit_utilization: 120,
              over_limit: true,
            },
            {
              id: 2,
              name: "Касса кафе",
              business_id: 2,
              business_name: "Кафе",
              balance: "3000.00",
              month_turnover: "40000.00",
              turnover_limit: "100000.00",
              limit_utilization: 40,
              over_limit: false,
            },
          ],
          total_balance: "8000.00",
          total_month_turnover: "160000.00",
        }),
      ),
    );
    renderWithProviders(<ReportsPage />);

    await userEvent.click(screen.getByRole("tab", { name: "Кассы" }));

    expect(await screen.findByText("Основная касса")).toBeInTheDocument();
    // ровно один badge превышения — у кассы, вышедшей за лимит
    expect(screen.getAllByText("Лимит превышен")).toHaveLength(1);
    expect(screen.getByText(fm("8000.00"))).toBeInTheDocument();
  });

  it("ФНС-12: реестр долгов с badge Просрочен и итогом открытых долгов", async () => {
    mockCashflowHandlers();
    server.use(
      http.get("/api/v1/reports/debts", () =>
        HttpResponse.json({
          debts: [
            {
              id: 1,
              debtor_name: "Кафе",
              creditor_name: "Мебель",
              amount: "5000.00",
              remaining: "4000.00",
              is_overdue: true,
              created_at: "2026-05-01T10:00:00Z",
            },
            {
              id: 2,
              debtor_name: "Мебель",
              creditor_name: "Кафе",
              amount: "2000.00",
              remaining: "2000.00",
              is_overdue: false,
              created_at: "2026-06-15T10:00:00Z",
            },
          ],
          pairs: [
            {
              debtor_name: "Кафе",
              creditor_name: "Мебель",
              total_remaining: "4000.00",
              debts_count: 1,
            },
          ],
          total_open: "6000.00",
        }),
      ),
    );
    renderWithProviders(<ReportsPage />);

    await userEvent.click(screen.getByRole("tab", { name: "Взаиморасчёты" }));

    expect(await screen.findByText("Просрочен")).toBeInTheDocument();
    expect(screen.getByText("Открыт")).toBeInTheDocument();
    expect(screen.getByText(fm("6000.00"))).toBeInTheDocument();
    expect(screen.getAllByText(fm("4000.00")).length).toBeGreaterThan(0);
  });

  it("ФНС-13: фонд по бизнесам, fund_total и прибыль по холдингу", async () => {
    mockCashflowHandlers();
    server.use(
      http.get("/api/v1/reports/payroll", () =>
        HttpResponse.json({
          period: { year: 2026, month: 6, status: "finalized" },
          fund_by_business: [
            {
              business_id: 1,
              business_name: "Мебель",
              base: "800.00",
              bonus: "200.00",
              fund: "1000.00",
            },
            {
              business_id: 2,
              business_name: "Кафе",
              base: "400.00",
              bonus: "100.00",
              fund: "500.00",
            },
          ],
          fund_total: "1500.00",
          profit_by_business: [
            {
              business_id: 1,
              business_name: "Мебель",
              income: "50000.00",
              expense: "20000.00",
              profit: "30000.00",
            },
          ],
          profit_total: { income: "50000.00", expense: "20000.00", profit: "30000.00" },
          runs: [],
        }),
      ),
    );
    renderWithProviders(<ReportsPage />);

    await userEvent.click(screen.getByRole("tab", { name: "Зарплатный фонд" }));

    expect(await screen.findByText(fm("1000.00"))).toBeInTheDocument();
    expect(screen.getByText(fm("500.00"))).toBeInTheDocument();
    expect(screen.getByText(fm("1500.00"))).toBeInTheDocument();
    expect(screen.getByText("Итого по холдингу")).toBeInTheDocument();
    expect(screen.getByText("Утверждён")).toBeInTheDocument();
  });

  it("i18n: при tj показывает таджикский заголовок", async () => {
    mockCashflowHandlers();
    await i18n.changeLanguage("tj");
    try {
      renderWithProviders(<ReportsPage />);
      expect((await screen.findAllByText("Мебель")).length).toBeGreaterThan(0);
      expect(screen.getByRole("heading", { name: "Ҳисоботҳо" })).toBeInTheDocument();
    } finally {
      await i18n.changeLanguage("ru");
    }
  });
});
