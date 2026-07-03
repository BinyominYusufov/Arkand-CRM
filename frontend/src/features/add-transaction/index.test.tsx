import { fireEvent, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";

import type { TransactionCreateInput } from "@/entities/transaction";
import { server } from "@/shared/test/msw";
import { renderWithProviders } from "@/shared/test/render";

import { AddTransactionControls } from "./index";

const ME = {
  id: 1,
  email: "fin@arkand.tj",
  username: "fin",
  full_name: "Финансист",
  phone: "",
  role: "financier",
  business: null,
  businesses: [],
  permissions: ["finance.view", "finance.manage"],
  cash_register_ids: [],
};

const BUSINESSES = [
  { id: 1, name: "Кафе Арканд", code: "cafe", kind: "cafe", kind_display: "Кафе", is_active: true },
];

const CATEGORIES = [{ id: 3, name: "Аренда", code: "rent" }];

function useBaseHandlers() {
  server.use(
    http.get("/api/v1/me", () => HttpResponse.json(ME)),
    http.get("/api/v1/businesses/", () => HttpResponse.json(BUSINESSES)),
    http.get("/api/v1/finance/categories/", () => HttpResponse.json(CATEGORIES)),
  );
}

beforeEach(() => {
  localStorage.setItem("arkand_access", "test-token");
});

describe("AddTransactionControls", () => {
  it("скрыт без права finance.manage (владелец read-only)", async () => {
    server.use(
      http.get("/api/v1/me", () =>
        HttpResponse.json({ ...ME, permissions: ["finance.view"] }),
      ),
    );
    renderWithProviders(<AddTransactionControls />);
    await waitFor(() => {
      expect(screen.queryByText("Добавить приход")).not.toBeInTheDocument();
    });
  });

  it("для расхода категория обязательна (Zod-ошибка)", async () => {
    useBaseHandlers();
    renderWithProviders(<AddTransactionControls />);

    fireEvent.click(await screen.findByText("Добавить расход"));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    await screen.findByRole("option", { name: "Кафе Арканд" });

    fireEvent.change(screen.getByLabelText("Бизнес"), { target: { value: "1" } });
    fireEvent.change(screen.getByLabelText("Сумма"), { target: { value: "100" } });
    fireEvent.click(screen.getByText("Сохранить"));

    expect(
      await screen.findByText("Для расхода обязательна категория"),
    ).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("успешный сабмит POST-ит операцию и закрывает модалку", async () => {
    useBaseHandlers();
    const bodies: TransactionCreateInput[] = [];
    server.use(
      http.post("/api/v1/finance/transactions/", async ({ request }) => {
        const body = (await request.json()) as TransactionCreateInput;
        bodies.push(body);
        return HttpResponse.json({ id: 10, ...body }, { status: 201 });
      }),
    );
    renderWithProviders(<AddTransactionControls />);

    fireEvent.click(await screen.findByText("Добавить приход"));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    await screen.findByRole("option", { name: "Кафе Арканд" });

    fireEvent.change(screen.getByLabelText("Бизнес"), { target: { value: "1" } });
    fireEvent.change(screen.getByLabelText("Сумма"), { target: { value: "250,50" } });
    fireEvent.change(screen.getByLabelText("Способ оплаты"), {
      target: { value: "transfer" },
    });
    fireEvent.click(screen.getByText("Сохранить"));

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
    expect(bodies).toHaveLength(1);
    expect(bodies[0]).toMatchObject({
      business: 1,
      kind: "income",
      category: null,
      amount: "250.50",
      method: "transfer",
    });
  });

  it("ошибка API 500 показывает ErrorBanner, модалка остаётся", async () => {
    useBaseHandlers();
    server.use(
      http.post("/api/v1/finance/transactions/", () =>
        HttpResponse.json(
          { code: "server_error", message: "Внутренняя ошибка сервера" },
          { status: 500 },
        ),
      ),
    );
    renderWithProviders(<AddTransactionControls />);

    fireEvent.click(await screen.findByText("Добавить приход"));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    await screen.findByRole("option", { name: "Кафе Арканд" });

    fireEvent.change(screen.getByLabelText("Бизнес"), { target: { value: "1" } });
    fireEvent.change(screen.getByLabelText("Сумма"), { target: { value: "100" } });
    fireEvent.click(screen.getByText("Сохранить"));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Внутренняя ошибка сервера",
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});
