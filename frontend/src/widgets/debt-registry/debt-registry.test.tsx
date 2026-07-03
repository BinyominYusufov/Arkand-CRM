import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "@/shared/test/msw";
import { renderWithProviders } from "@/shared/test/render";

import { DebtRegistry } from "./index";

const registry = {
  debts: [
    {
      id: 1,
      debtor_id: 1,
      debtor_name: "Кафе Восток",
      creditor_id: 2,
      creditor_name: "Автомойка",
      amount: "1000.00",
      remaining: "400.00",
      is_overdue: true,
      created_at: "2026-06-01T10:00:00Z",
      source_transfer_id: 5,
    },
    {
      id: 2,
      debtor_id: 2,
      debtor_name: "Автомойка",
      creditor_id: 3,
      creditor_name: "Пекарня",
      amount: "500.00",
      remaining: "500.00",
      is_overdue: false,
      created_at: "2026-06-10T10:00:00Z",
      source_transfer_id: null,
    },
  ],
  pairs: [
    {
      debtor_id: 1,
      debtor_name: "Кафе Восток",
      creditor_id: 2,
      creditor_name: "Автомойка",
      total_remaining: "400.00",
      debts_count: 1,
    },
    {
      debtor_id: 2,
      debtor_name: "Автомойка",
      creditor_id: 3,
      creditor_name: "Пекарня",
      total_remaining: "500.00",
      debts_count: 1,
    },
  ],
  total_open: "900.00",
};

function mockRegistry() {
  server.use(
    http.get("/api/v1/settlements/debts/registry/", () => HttpResponse.json(registry)),
  );
}

describe("DebtRegistry", () => {
  it("рендерит пары «кто кому должен», долги и бейдж «Просрочен» при is_overdue", async () => {
    mockRegistry();
    renderWithProviders(<DebtRegistry />);

    // Пара + строка долга — имя должника встречается дважды.
    expect(await screen.findAllByText("Кафе Восток")).toHaveLength(2);
    expect(screen.getAllByText("Пекарня")).toHaveLength(2);
    // Итог открытых долгов.
    expect(screen.getByText("Открытых долгов на сумму")).toBeInTheDocument();
    expect(screen.getByText(/900,00/)).toBeInTheDocument();
    // Бейдж «Просрочен» — только у первого долга.
    expect(screen.getAllByText("Просрочен")).toHaveLength(1);
    // Кнопка неттинга на месте.
    expect(screen.getByRole("button", { name: "Провести неттинг" })).toBeInTheDocument();
  });

  it("закрытие долга отправляет POST settle с выбранным методом и суммой", async () => {
    mockRegistry();
    let body: Record<string, unknown> | null = null;
    server.use(
      http.post("/api/v1/settlements/debts/1/settle/", async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ id: 1, status: "closed" });
      }),
    );
    const user = userEvent.setup();
    renderWithProviders(<DebtRegistry />);

    await screen.findAllByText("Кафе Восток");
    await user.click(screen.getAllByLabelText("Закрыть долг")[0]);

    const dialog = screen.getByRole("dialog", { name: "Закрыть долг" });
    await user.selectOptions(within(dialog).getByLabelText("Способ погашения"), "return");
    await user.type(within(dialog).getByLabelText(/Сумма/), "150");
    await user.click(within(dialog).getByRole("button", { name: "Закрыть долг" }));

    await waitFor(() => expect(body).toMatchObject({ method: "return", amount: "150" }));
    // Модалка закрылась после успеха.
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });
});
