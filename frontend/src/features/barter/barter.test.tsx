import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "@/shared/test/msw";
import { renderWithProviders } from "@/shared/test/render";

import { BarterSection } from "./index";

const barters = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: 1,
      business_a: 1,
      business_a_name: "Кафе Восток",
      business_b: 2,
      business_b_name: "Автомойка",
      description: "Обмен услугами",
      value: "2500.00",
      controlled_by: 7,
      controlled_by_name: "Бухгалтер",
      status: "active",
      created_at: "2026-06-15T10:00:00Z",
    },
    {
      id: 2,
      business_a: 2,
      business_a_name: "Автомойка",
      business_b: 3,
      business_b_name: "Пекарня",
      description: "Хлеб за мойку",
      value: "700.00",
      controlled_by: 7,
      controlled_by_name: "Бухгалтер",
      status: "completed",
      created_at: "2026-06-16T10:00:00Z",
    },
  ],
};

const openDebts = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: 10,
      debtor: 2,
      debtor_name: "Автомойка",
      creditor: 1,
      creditor_name: "Кафе Восток",
      amount: "1000.00",
      remaining: "300.00",
      status: "open",
      is_overdue: false,
      source_transfer: null,
      settlements: [],
      created_at: "2026-06-01T10:00:00Z",
      closed_at: null,
    },
    {
      id: 11,
      debtor: 3,
      debtor_name: "Пекарня",
      creditor: 4,
      creditor_name: "Ателье",
      amount: "900.00",
      remaining: "900.00",
      status: "open",
      is_overdue: false,
      source_transfer: null,
      settlements: [],
      created_at: "2026-06-02T10:00:00Z",
      closed_at: null,
    },
  ],
};

function mockApi() {
  server.use(
    http.get("/api/v1/settlements/barters/", () => HttpResponse.json(barters)),
    http.get("/api/v1/settlements/debts/", () => HttpResponse.json(openDebts)),
  );
}

describe("BarterSection", () => {
  it("рендерит бартеры: стороны, оценка, статусы; действия только у активного", async () => {
    mockApi();
    renderWithProviders(<BarterSection />);

    expect(await screen.findByText("Обмен услугами")).toBeInTheDocument();
    expect(screen.getByText("Активен")).toBeInTheDocument();
    expect(screen.getByText("Завершён")).toBeInTheDocument();
    expect(screen.getByText(/2 500,00/)).toBeInTheDocument();
    // Действия — только у активного бартера.
    expect(screen.getAllByLabelText("Завершить")).toHaveLength(1);
    expect(screen.getAllByLabelText("Отменить")).toHaveLength(1);
    expect(screen.getAllByLabelText("Закрыть долг бартером")).toHaveLength(1);
  });

  it("закрытие долга бартером: в списке только долги той же пары, отправляет close-debt", async () => {
    mockApi();
    let body: Record<string, unknown> | null = null;
    server.use(
      http.post("/api/v1/settlements/barters/1/close-debt/", async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({});
      }),
    );
    const user = userEvent.setup();
    renderWithProviders(<BarterSection />);

    await user.click(await screen.findByLabelText("Закрыть долг бартером"));
    const dialog = await screen.findByRole("dialog", { name: "Закрыть долг бартером" });

    const select = await within(dialog).findByLabelText("Долг");
    const options = within(select).getAllByRole("option");
    // Пустая опция + один долг пары «Кафе Восток — Автомойка»; долг Пекарня-Ателье отфильтрован.
    expect(options).toHaveLength(2);
    expect(within(select).queryByText(/Ателье/)).not.toBeInTheDocument();

    await user.selectOptions(select, "10");
    await user.click(within(dialog).getByRole("button", { name: "Закрыть долг" }));

    await waitFor(() => expect(body).toMatchObject({ debt: 10 }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });
});
