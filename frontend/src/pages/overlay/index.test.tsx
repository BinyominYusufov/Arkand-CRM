import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { formatMoney } from "@/shared/lib/money";
import { server } from "@/shared/test/msw";
import { renderWithProviders } from "@/shared/test/render";

import { OverlayPage } from "./index";

/* Testing-library нормализует NBSP в обычные пробелы — приводим ожидания к тому же виду. */
const normalizeSpaces = (s: string) => s.replace(/\s/g, " ");
const fm = (value: string) => normalizeSpaces(formatMoney(value));

/* Recharts ResponsiveContainer требует ResizeObserver, которого нет в jsdom. */
vi.stubGlobal(
  "ResizeObserver",
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  },
);

const summaryFixture = {
  businesses: [
    {
      business_id: 1,
      business_name: "Мебель",
      income: "55555.00",
      expense: "11111.00",
      profit: "44444.50",
    },
    {
      business_id: 2,
      business_name: "Кафе",
      income: "55556.00",
      expense: "11111.00",
      profit: "44444.50",
    },
  ],
  total: { income: "111111.00", expense: "22222.00", profit: "88889.00" },
  open_debts_total: "3333.00",
  cash_balance_total: "44444.00",
  businesses_count: 2,
};

const cashFixture = {
  registers: [
    {
      id: 1,
      name: "Основная касса",
      business_id: 1,
      business_name: "Мебель",
      balance: "44444.00",
      month_turnover: "1000.00",
      turnover_limit: "100000.00",
      limit_utilization: 1,
      over_limit: false,
    },
  ],
  total_balance: "44444.00",
  total_month_turnover: "1000.00",
};

const debtsFixture = {
  debts: [],
  pairs: [
    {
      debtor_name: "Кафе",
      creditor_name: "Мебель",
      total_remaining: "3333.00",
      debts_count: 2,
    },
  ],
  total_open: "3333.00",
};

const payrollFixture = {
  period: null,
  fund_by_business: [
    {
      business_id: 1,
      business_name: "Мебель",
      base: "700.00",
      bonus: "77.00",
      fund: "777.00",
    },
  ],
  fund_total: "777.00",
  profit_by_business: [],
  profit_total: { income: "0.00", expense: "0.00", profit: "0.00" },
  runs: [],
};

function mockOverlayHandlers() {
  server.use(
    http.get("/api/v1/overlay/summary", () => HttpResponse.json(summaryFixture)),
    http.get("/api/v1/overlay/cash", () => HttpResponse.json(cashFixture)),
    http.get("/api/v1/overlay/debts", () => HttpResponse.json(debtsFixture)),
    http.get("/api/v1/overlay/payroll", () => HttpResponse.json(payrollFixture)),
  );
}

describe("OverlayPage", () => {
  it("KPI-строка рендерит все 5 консолидированных значений", async () => {
    mockOverlayHandlers();
    renderWithProviders(<OverlayPage />);

    expect((await screen.findAllByText("Доходы")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Расходы").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Прибыль").length).toBeGreaterThan(0);
    expect(screen.getByText("Открытые долги")).toBeInTheDocument();
    expect(screen.getByText("Остатки в кассах")).toBeInTheDocument();

    expect(screen.getByText(fm("111111.00"))).toBeInTheDocument();
    expect(screen.getByText(fm("22222.00"))).toBeInTheDocument();
    expect(screen.getAllByText(fm("88889.00")).length).toBeGreaterThan(0);
    expect(screen.getAllByText(fm("3333.00")).length).toBeGreaterThan(0);
    expect(screen.getAllByText(fm("44444.00")).length).toBeGreaterThan(0);
  });

  it("секции касс, долгов и зарплатного фонда рендерят данные", async () => {
    mockOverlayHandlers();
    renderWithProviders(<OverlayPage />);

    expect(await screen.findByText("Основная касса")).toBeInTheDocument();
    // пара долгов: Кафе должно Мебели
    expect(screen.getAllByText("Кафе").length).toBeGreaterThan(0);
    // зарплатный фонд
    expect(screen.getByText(fm("700.00"))).toBeInTheDocument();
    expect(screen.getAllByText(fm("777.00")).length).toBeGreaterThan(0);
  });

  it("Экспорт консолидации вызывает GET /overlay/export", async () => {
    mockOverlayHandlers();
    const exportSpy = vi.fn();
    server.use(
      http.get("/api/v1/overlay/export", () => {
        exportSpy();
        return HttpResponse.json({ version: 1, businesses: [] });
      }),
    );
    const createObjectURL = vi.fn(() => "blob:arkand");
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});

    renderWithProviders(<OverlayPage />);
    await screen.findAllByText("Доходы");

    await userEvent.click(
      screen.getByRole("button", { name: "Экспорт консолидации" }),
    );

    await waitFor(() => expect(exportSpy).toHaveBeenCalledTimes(1));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    clickSpy.mockRestore();
  });

  it("ошибка API показывает ErrorBanner", async () => {
    server.use(
      http.get("/api/v1/overlay/summary", () =>
        HttpResponse.json(
          { code: "forbidden", message: "Недостаточно прав" },
          { status: 403 },
        ),
      ),
      http.get("/api/v1/overlay/cash", () => HttpResponse.json(cashFixture)),
      http.get("/api/v1/overlay/debts", () => HttpResponse.json(debtsFixture)),
      http.get("/api/v1/overlay/payroll", () => HttpResponse.json(payrollFixture)),
    );
    renderWithProviders(<OverlayPage />);

    expect(await screen.findByText("Недостаточно прав")).toBeInTheDocument();
  });
});
