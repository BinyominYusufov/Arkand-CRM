import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "@/shared/test/msw";
import { renderWithProviders } from "@/shared/test/render";

import { TransfersSection } from "./index";

const transfers = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: 1,
      from_business: 1,
      from_business_name: "Кафе Восток",
      to_business: 2,
      to_business_name: "Автомойка",
      amount: "15000.00",
      status: "pending",
      requires_owner_approval: true,
      note: "",
      created_by_name: "Бухгалтер",
      approved_by_name: "",
      created_at: "2026-06-20T10:00:00Z",
    },
    {
      id: 2,
      from_business: 2,
      from_business_name: "Автомойка",
      to_business: 3,
      to_business_name: "Пекарня",
      amount: "300.00",
      status: "approved",
      requires_owner_approval: false,
      note: "",
      created_by_name: "Бухгалтер",
      approved_by_name: "Владелец",
      created_at: "2026-06-21T10:00:00Z",
    },
  ],
};

function mockApi(permissions: string[]) {
  localStorage.setItem("arkand_access", "test-token");
  server.use(
    http.get("/api/v1/me", () =>
      HttpResponse.json({
        id: 7,
        email: "acc@arkand.tj",
        username: "acc",
        full_name: "Бухгалтер",
        phone: "",
        role: "accountant",
        business: null,
        businesses: [],
        permissions,
        cash_register_ids: [],
      }),
    ),
    http.get("/api/v1/settlements/transfers/", () => HttpResponse.json(transfers)),
    http.get("/api/v1/businesses/", () =>
      HttpResponse.json([
        { id: 1, name: "Кафе Восток", code: "cafe", kind: "cafe", kind_display: "Кафе", is_active: true },
        { id: 2, name: "Автомойка", code: "wash", kind: "carwash", kind_display: "Мойка", is_active: true },
      ]),
    ),
  );
}

describe("TransfersSection", () => {
  it("показывает кнопки одобрения pending-передачи при праве settlements.approve", async () => {
    mockApi(["settlements.approve"]);
    renderWithProviders(<TransfersSection />);

    expect(await screen.findByText("Кафе Восток")).toBeInTheDocument();
    expect(await screen.findAllByLabelText("Одобрить передачу")).toHaveLength(1);
    expect(screen.getAllByLabelText("Отклонить передачу")).toHaveLength(1);
    // Бейдж «требует одобрения владельца» — у первой передачи.
    expect(screen.getByText("Требует одобрения владельца")).toBeInTheDocument();
  });

  it("скрывает кнопки одобрения и создание без прав", async () => {
    mockApi([]);
    renderWithProviders(<TransfersSection />);

    expect(await screen.findByText("Кафе Восток")).toBeInTheDocument();
    expect(screen.queryByLabelText("Одобрить передачу")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Отклонить передачу")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Новая передача" }),
    ).not.toBeInTheDocument();
  });

  it("показывает ErrorBanner при 403 owner_approval_required на одобрении", async () => {
    mockApi(["settlements.approve"]);
    server.use(
      http.post("/api/v1/settlements/transfers/1/approve/", () =>
        HttpResponse.json(
          { code: "owner_approval_required", message: "forbidden" },
          { status: 403 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderWithProviders(<TransfersSection />);

    await user.click(await screen.findByLabelText("Одобрить передачу"));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "Сумма сверх порога — одобрить может только владелец",
    );
  });

  it("форма передачи не даёт выбрать одинаковые бизнесы (Zod) и не шлёт запрос", async () => {
    mockApi(["settlements.manage"]);
    let posted = false;
    server.use(
      http.post("/api/v1/settlements/transfers/", () => {
        posted = true;
        return HttpResponse.json({});
      }),
    );
    const user = userEvent.setup();
    renderWithProviders(<TransfersSection />);

    await user.click(await screen.findByRole("button", { name: "Новая передача" }));
    const dialog = screen.getByRole("dialog", { name: "Новая передача" });
    await user.selectOptions(within(dialog).getByLabelText("Откуда"), "1");
    await user.selectOptions(within(dialog).getByLabelText("Куда"), "1");
    await user.type(within(dialog).getByLabelText("Сумма"), "100");
    await user.click(within(dialog).getByRole("button", { name: "Создать" }));

    expect(within(dialog).getByText("Ошибка")).toBeInTheDocument();
    expect(posted).toBe(false);
  });
});
