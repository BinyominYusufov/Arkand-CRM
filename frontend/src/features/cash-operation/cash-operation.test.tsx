import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import type { CashRegister } from "@/entities/cash-register";
import { renderWithProviders } from "@/shared/test/render";
import { server } from "@/shared/test/msw";

import { CashOperationModal } from "./index";

const registers: CashRegister[] = [
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
];

describe("CashOperationModal", () => {
  it("валидирует, что сумма должна быть больше нуля", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <CashOperationModal open onClose={() => {}} registers={registers} />,
    );
    await user.selectOptions(screen.getByLabelText("Касса"), "1");
    await user.click(screen.getByRole("button", { name: "Сохранить" }));
    expect(
      await screen.findByText("Сумма должна быть больше нуля"),
    ).toBeInTheDocument();

    await user.type(screen.getByLabelText("Сумма"), "-5");
    await user.click(screen.getByRole("button", { name: "Сохранить" }));
    expect(
      await screen.findByText("Сумма должна быть больше нуля"),
    ).toBeInTheDocument();
  });

  it("требует выбрать кассу", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <CashOperationModal open onClose={() => {}} registers={registers} />,
    );
    await user.type(screen.getByLabelText("Сумма"), "100");
    await user.click(screen.getByRole("button", { name: "Сохранить" }));
    expect(await screen.findByText("Обязательное поле")).toBeInTheDocument();
  });

  it("показывает ErrorBanner при 400 cash_limit_exceeded", async () => {
    server.use(
      http.post("/api/v1/cash/operations/", () =>
        HttpResponse.json(
          {
            code: "cash_limit_exceeded",
            message: "Cash limit exceeded",
            details: { limit: "50000.00" },
          },
          { status: 400 },
        ),
      ),
    );
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderWithProviders(
      <CashOperationModal open onClose={onClose} registers={registers} />,
    );
    await user.selectOptions(screen.getByLabelText("Касса"), "1");
    await user.click(screen.getByLabelText("Расход"));
    await user.type(screen.getByLabelText("Сумма"), "1000");
    await user.click(screen.getByRole("button", { name: "Сохранить" }));

    const banner = await screen.findByRole("alert");
    expect(banner).toHaveTextContent("Превышен лимит оборота кассы");
    expect(banner).toHaveTextContent("50000.00");
    expect(onClose).not.toHaveBeenCalled();
  });

  it("показывает ErrorBanner при insufficient_funds", async () => {
    server.use(
      http.post("/api/v1/cash/operations/", () =>
        HttpResponse.json(
          {
            code: "insufficient_funds",
            message: "Insufficient funds",
            details: { balance: "12500.00" },
          },
          { status: 400 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderWithProviders(
      <CashOperationModal open onClose={() => {}} registers={registers} />,
    );
    await user.selectOptions(screen.getByLabelText("Касса"), "1");
    await user.click(screen.getByLabelText("Расход"));
    await user.type(screen.getByLabelText("Сумма"), "99999");
    await user.click(screen.getByRole("button", { name: "Сохранить" }));

    const banner = await screen.findByRole("alert");
    expect(banner).toHaveTextContent("Недостаточно средств в кассе");
  });
});
