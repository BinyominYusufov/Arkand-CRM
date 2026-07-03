import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { server } from "@/shared/test/msw";
import { renderWithProviders } from "@/shared/test/render";

import { RunPayrollButton } from "./index";

const createdRun = {
  id: 7,
  year: 2026,
  month: 7,
  status: "draft",
  paid_from_hq: true,
  created_at: "2026-07-03T00:00:00Z",
  finalized_at: null,
  total_fund: "0.00",
  items_count: 0,
  items: [],
};

describe("RunPayrollButton", () => {
  it("отправляет POST с year/month (дефолт — текущий период) и отдаёт созданный расчёт", async () => {
    const user = userEvent.setup();
    let body: unknown;
    server.use(
      http.post("/api/v1/payroll/runs/", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(createdRun, { status: 201 });
      }),
    );
    const onCreated = vi.fn();
    renderWithProviders(<RunPayrollButton onCreated={onCreated} />);

    await user.click(screen.getByRole("button", { name: "Запустить расчёт зарплаты" }));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Создать" }));

    await waitFor(() => expect(onCreated).toHaveBeenCalled());
    const now = new Date();
    expect(body).toEqual({ year: now.getFullYear(), month: now.getMonth() + 1 });
    expect(onCreated).toHaveBeenCalledWith(expect.objectContaining({ id: 7 }));
    // модалка закрылась
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("валидация Zod: пустой год — ошибка, запрос не уходит", async () => {
    const user = userEvent.setup();
    let called = false;
    server.use(
      http.post("/api/v1/payroll/runs/", () => {
        called = true;
        return HttpResponse.json(createdRun, { status: 201 });
      }),
    );
    renderWithProviders(<RunPayrollButton />);

    await user.click(screen.getByRole("button", { name: "Запустить расчёт зарплаты" }));
    const dialog = screen.getByRole("dialog");
    await user.clear(within(dialog).getByLabelText("Год"));
    await user.click(within(dialog).getByRole("button", { name: "Создать" }));

    expect(within(dialog).getByText("Обязательное поле")).toBeInTheDocument();
    expect(called).toBe(false);
  });

  it("409 при создании показывает ErrorBanner", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/v1/payroll/runs/", () =>
        HttpResponse.json(
          { code: "conflict", message: "Run already finalized" },
          { status: 409 },
        ),
      ),
    );
    renderWithProviders(<RunPayrollButton />);

    await user.click(screen.getByRole("button", { name: "Запустить расчёт зарплаты" }));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Создать" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "Расчёт за этот период уже утверждён",
    );
  });
});
