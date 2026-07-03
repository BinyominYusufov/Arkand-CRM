import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { PayrollItem } from "@/entities/payroll";
import { formatMoney } from "@/shared/lib/money";
import { renderWithProviders } from "@/shared/test/render";

import { PayrollTable } from "./index";

/** RTL нормализует NBSP из Intl в обычные пробелы. */
const money = (v: string) => formatMoney(v).replace(/\s+/g, " ");

const items: PayrollItem[] = [
  {
    id: 1,
    employee: 10,
    employee_name: "Иванов Иван",
    business_name: "Магазин",
    salary_type: "objective",
    base: "3000.00",
    bonus: "450.50",
    total: "3450.50",
    breakdown: {
      scheme_type: "per_unit_tiered",
      tier_mode: "progressive",
      inputs: { units: { value: 120, source: "manual" } },
      tiers_applied: [{ up_to: 100, rate: "10.00" }],
    },
  },
  {
    id: 2,
    employee: 11,
    employee_name: "Петров Пётр",
    business_name: null,
    salary_type: "administrative",
    base: "5000.00",
    bonus: "0.00",
    total: "5000.00",
    breakdown: { scheme_type: "fixed" },
  },
];

describe("PayrollTable", () => {
  it("рендерит base/bonus/total через formatMoney и головной офис для business=null", () => {
    renderWithProviders(<PayrollTable items={items} />);

    expect(screen.getByText(money("3000.00"))).toBeInTheDocument();
    expect(screen.getByText(money("450.50"))).toBeInTheDocument();
    expect(screen.getByText(money("3450.50"))).toBeInTheDocument();
    // base и total второй строки совпадают
    expect(screen.getAllByText(money("5000.00"))).toHaveLength(2);
    expect(screen.getByText("Головной офис")).toBeInTheDocument();
    expect(screen.getByText("Объектный")).toBeInTheDocument();
    expect(screen.getByText("Административный")).toBeInTheDocument();
  });

  it("раскрывает разбивку: показывает tier_mode, тип схемы и источник данных", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PayrollTable items={items} />);

    expect(screen.queryByText("progressive")).not.toBeInTheDocument();

    const toggles = screen.getAllByRole("button", { name: "Разбивка" });
    await user.click(toggles[0]);

    expect(screen.getByText("progressive")).toBeInTheDocument();
    expect(screen.getByText("За единицу со ступенями")).toBeInTheDocument();
    expect(screen.getByText("(Источник данных: Вручную)")).toBeInTheDocument();

    // повторный клик сворачивает
    await user.click(screen.getAllByRole("button", { name: "Разбивка" })[0]);
    expect(screen.queryByText("progressive")).not.toBeInTheDocument();
  });
});
