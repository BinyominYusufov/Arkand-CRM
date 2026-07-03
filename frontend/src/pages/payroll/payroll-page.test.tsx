import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import type { PayrollRun } from "@/entities/payroll";
import { formatMoney } from "@/shared/lib/money";
import { server } from "@/shared/test/msw";
import { renderWithProviders } from "@/shared/test/render";

import { PayrollPage } from "./index";

/** RTL нормализует NBSP из Intl в обычные пробелы. */
const money = (v: string) => formatMoney(v).replace(/\s+/g, " ");

const me = {
  id: 1,
  email: "owner@arkand.tj",
  username: "owner",
  full_name: "Владелец",
  phone: "",
  role: "owner",
  business: null,
  businesses: [],
  permissions: ["payroll.view", "payroll.manage"],
  cash_register_ids: [],
};

const items = [
  {
    id: 1,
    employee: 10,
    employee_name: "Иванов Иван",
    business_name: "Магазин",
    salary_type: "objective",
    base: "3000.00",
    bonus: "450.50",
    total: "3450.50",
    breakdown: { scheme_type: "fixed" },
  },
];

function makeRun(status: "draft" | "finalized"): PayrollRun {
  return {
    id: 1,
    year: 2026,
    month: 6,
    status,
    paid_from_hq: true,
    created_at: "2026-06-30T00:00:00Z",
    finalized_at: status === "finalized" ? "2026-07-01T00:00:00Z" : null,
    total_fund: "3450.50",
    items_count: 1,
    items,
  };
}

function mockApi(run: PayrollRun) {
  localStorage.setItem("arkand_access", "test-token");
  server.use(
    http.get("/api/v1/me", () => HttpResponse.json(me)),
    http.get("/api/v1/payroll/runs/", () =>
      HttpResponse.json({ count: 1, next: null, previous: null, results: [run] }),
    ),
    http.get(`/api/v1/payroll/runs/${run.id}/`, () => HttpResponse.json(run)),
  );
}

describe("PayrollPage", () => {
  it("список расчётов: период, статус, фонд; детали открываются, для draft есть кнопка Утвердить", async () => {
    const user = userEvent.setup();
    mockApi(makeRun("draft"));
    renderWithProviders(<PayrollPage />);

    expect(await screen.findByText("06.2026")).toBeInTheDocument();
    expect(screen.getByText("Черновик")).toBeInTheDocument();
    expect(screen.getByText(money("3450.50"))).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Просмотр" }));

    expect(await screen.findByText("Иванов Иван")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Утвердить" })).toBeInTheDocument();
  });

  it("для утверждённого расчёта кнопки Утвердить нет", async () => {
    const user = userEvent.setup();
    mockApi(makeRun("finalized"));
    renderWithProviders(<PayrollPage />);

    await user.click(await screen.findByRole("button", { name: "Просмотр" }));

    expect(await screen.findByText("Иванов Иван")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Утвердить" })).not.toBeInTheDocument();
  });

  it("409 при утверждении показывает ErrorBanner «уже утверждён»", async () => {
    const user = userEvent.setup();
    mockApi(makeRun("draft"));
    server.use(
      http.post("/api/v1/payroll/runs/1/finalize/", () =>
        HttpResponse.json(
          { code: "conflict", message: "Already finalized" },
          { status: 409 },
        ),
      ),
    );
    renderWithProviders(<PayrollPage />);

    await user.click(await screen.findByRole("button", { name: "Просмотр" }));
    await user.click(await screen.findByRole("button", { name: "Утвердить" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Расчёт за этот период уже утверждён",
    );
  });

  it("таб Сотрудники: рендер, бейдж продажника и фильтр активности", async () => {
    const user = userEvent.setup();
    mockApi(makeRun("draft"));
    const requestedFilters: (string | null)[] = [];
    server.use(
      http.get("/api/v1/payroll/employees/", ({ request }) => {
        requestedFilters.push(new URL(request.url).searchParams.get("is_active"));
        return HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 5,
              full_name: "Сидорова Анна",
              business: 2,
              business_name: "Кафе",
              position: "Продавец",
              salary_type: "objective",
              is_salesperson: true,
              is_active: true,
            },
          ],
        });
      }),
    );
    renderWithProviders(<PayrollPage />);

    await user.click(screen.getByRole("tab", { name: "Сотрудники" }));

    expect(await screen.findByText("Сидорова Анна")).toBeInTheDocument();
    expect(screen.getByText("Продажник")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Активен"), "1");
    expect(await screen.findByText("Сидорова Анна")).toBeInTheDocument();
    expect(requestedFilters).toContain("true");
  });
});
