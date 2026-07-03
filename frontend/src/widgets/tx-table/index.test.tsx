import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";

import type { Transaction } from "@/entities/transaction";
import { server } from "@/shared/test/msw";
import { renderWithProviders } from "@/shared/test/render";

import { TxTable } from "./index";

const ME = {
  id: 1,
  email: "fin@arkand.tj",
  username: "fin",
  full_name: "Финансист",
  phone: "",
  role: "financier",
  business: null,
  businesses: [],
  permissions: ["finance.view", "finance.manage", "finance.approve"],
  cash_register_ids: [],
};

const BUSINESSES = [
  { id: 1, name: "Кафе Арканд", code: "cafe", kind: "cafe", kind_display: "Кафе", is_active: true },
];

function tx(over: Partial<Transaction> = {}): Transaction {
  return {
    id: 1,
    business: 1,
    business_name: "Кафе Арканд",
    kind: "income",
    category: null,
    category_name: null,
    amount: "12345.67",
    method: "cash",
    status: "pending",
    confirmed_by: null,
    confirmed_by_name: "",
    created_by: 2,
    created_by_name: "Кассир Али",
    occurred_at: "2026-07-01T10:00:00Z",
    note: "",
    created_at: "2026-07-01T10:00:00Z",
    ...over,
  };
}

const paginated = (results: Transaction[]) => ({
  count: results.length,
  next: null,
  previous: null,
  results,
});

function useBaseHandlers(transactions: Transaction[]) {
  server.use(
    http.get("/api/v1/me", () => HttpResponse.json(ME)),
    http.get("/api/v1/businesses/", () => HttpResponse.json(BUSINESSES)),
    http.get("/api/v1/finance/transactions/", () =>
      HttpResponse.json(paginated(transactions)),
    ),
  );
}

beforeEach(() => {
  localStorage.setItem("arkand_access", "test-token");
});

describe("TxTable", () => {
  it("рендерит операции: форматированные суммы и data-direction", async () => {
    useBaseHandlers([
      tx(),
      tx({
        id: 2,
        kind: "expense",
        category: 3,
        category_name: "Аренда",
        amount: "500.00",
        method: "transfer",
        status: "confirmed",
      }),
    ]);
    renderWithProviders(<TxTable />);

    const income = await screen.findByText("+12 345,67 с.");
    expect(income).toHaveAttribute("data-direction", "in");

    const expense = screen.getByText("−500,00 с.");
    expect(expense).toHaveAttribute("data-direction", "out");

    const table = screen.getByRole("table");
    expect(screen.getAllByText("Кассир Али")).toHaveLength(2);
    expect(within(table).getByText("Аренда")).toBeInTheDocument();
    expect(within(table).getByText("Ожидает")).toBeInTheDocument();
    expect(within(table).getByText("Подтверждено")).toBeInTheDocument();
    expect(within(table).getByText("Перевод")).toBeInTheDocument();
  });

  it("фильтр по статусу дергает запрос с параметром status", async () => {
    const urls: string[] = [];
    server.use(
      http.get("/api/v1/me", () => HttpResponse.json(ME)),
      http.get("/api/v1/businesses/", () => HttpResponse.json(BUSINESSES)),
      http.get("/api/v1/finance/transactions/", ({ request }) => {
        urls.push(request.url);
        return HttpResponse.json(paginated([]));
      }),
    );
    renderWithProviders(<TxTable />);
    await screen.findByText("Данных нет");

    fireEvent.change(screen.getByLabelText("Статус"), {
      target: { value: "pending" },
    });

    await waitFor(() => {
      const withStatus = urls.map((u) => new URL(u).searchParams.get("status"));
      expect(withStatus).toContain("pending");
    });
  });

  it("кнопка подтверждения видна только для pending income", async () => {
    useBaseHandlers([
      tx({ id: 1, kind: "income", status: "pending" }),
      tx({ id: 2, kind: "income", status: "confirmed" }),
      tx({ id: 3, kind: "expense", status: "pending", category: 3, category_name: "Аренда" }),
    ]);
    renderWithProviders(<TxTable />);

    await screen.findAllByText("Кассир Али");
    expect(screen.getAllByLabelText("Подтвердить приход")).toHaveLength(1);
  });

  it("без права finance.approve кнопки подтверждения нет", async () => {
    server.use(
      http.get("/api/v1/me", () =>
        HttpResponse.json({ ...ME, permissions: ["finance.view"] }),
      ),
      http.get("/api/v1/businesses/", () => HttpResponse.json(BUSINESSES)),
      http.get("/api/v1/finance/transactions/", () =>
        HttpResponse.json(paginated([tx()])),
      ),
    );
    renderWithProviders(<TxTable />);

    await screen.findByText("Кассир Али");
    expect(screen.queryByLabelText("Подтвердить приход")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Удалить")).not.toBeInTheDocument();
  });

  it("409 при подтверждении показывает ErrorBanner", async () => {
    useBaseHandlers([tx()]);
    server.use(
      http.post("/api/v1/finance/transactions/1/confirm/", () =>
        HttpResponse.json(
          { code: "conflict", message: "Операция уже подтверждена" },
          { status: 409 },
        ),
      ),
    );
    renderWithProviders(<TxTable />);

    fireEvent.click(await screen.findByLabelText("Подтвердить приход"));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Операция уже подтверждена",
    );
  });
});
