import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "@/shared/test/msw";
import { renderWithProviders } from "@/shared/test/render";

import { SettlementsPage } from "./index";

describe("SettlementsPage", () => {
  it("рендерит заголовок, табы; по умолчанию — реестр, переключение на передачи", async () => {
    server.use(
      http.get("/api/v1/settlements/debts/registry/", () =>
        HttpResponse.json({
          debts: [],
          pairs: [
            {
              debtor_id: 1,
              debtor_name: "Кафе Восток",
              creditor_id: 2,
              creditor_name: "Автомойка",
              total_remaining: "400.00",
              debts_count: 1,
            },
          ],
          total_open: "400.00",
        }),
      ),
      http.get("/api/v1/settlements/transfers/", () =>
        HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 1,
              from_business: 1,
              from_business_name: "Пекарня",
              to_business: 2,
              to_business_name: "Ателье",
              amount: "100.00",
              status: "pending",
              requires_owner_approval: false,
              note: "",
              created_by_name: "",
              approved_by_name: "",
              created_at: "2026-06-20T10:00:00Z",
            },
          ],
        }),
      ),
    );
    const user = userEvent.setup();
    renderWithProviders(<SettlementsPage />);

    expect(
      screen.getByRole("heading", { name: "Взаиморасчёты" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("tab")).toHaveLength(3);
    // Таб по умолчанию — реестр долгов.
    expect(await screen.findByText("Кто кому должен")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Передачи" }));
    expect(await screen.findByText("Пекарня")).toBeInTheDocument();
    expect(screen.getByText("Ожидает")).toBeInTheDocument();
  });
});
