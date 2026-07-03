import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { CashRegister } from "@/entities/cash-register";
import { formatMoney } from "@/shared/lib/money";
import { renderWithProviders } from "@/shared/test/render";

import { CashCard } from "./index";

/** RTL нормализует NBSP из Intl.NumberFormat в обычный пробел. */
const norm = (s: string) => s.replace(/\s+/g, " ");

function makeRegister(overrides: Partial<CashRegister> = {}): CashRegister {
  return {
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
    ...overrides,
  };
}

describe("CashCard", () => {
  it("показывает остаток, лимит и оборот месяца без бейджа превышения", () => {
    renderWithProviders(<CashCard register={makeRegister()} />);
    expect(screen.getByText("Основная · Кафе Восток")).toBeInTheDocument();
    expect(screen.getByText(norm(formatMoney("12500.00")))).toBeInTheDocument();
    expect(screen.getByText("Лимит оборота")).toBeInTheDocument();
    expect(screen.getByText(norm(formatMoney("50000.00")))).toBeInTheDocument();
    expect(screen.getByText("Оборот за месяц")).toBeInTheDocument();
    expect(screen.getByText(norm(formatMoney("30000.00")))).toBeInTheDocument();
    expect(screen.queryByText("Лимит превышен")).not.toBeInTheDocument();
  });

  it("показывает бейдж «Лимит превышен» при over_limit", () => {
    renderWithProviders(
      <CashCard
        register={makeRegister({ over_limit: true, limit_utilization: 120 })}
      />,
    );
    const badge = screen.getByText("Лимит превышен");
    expect(badge).toBeInTheDocument();
    expect(badge.closest(".badge")).toHaveClass("badge--error");
  });

  it("меняет цвет прогресс-бара по заполнению лимита", () => {
    const cases: [number, string][] = [
      [50, "var(--success)"],
      [85, "var(--warning)"],
      [120, "var(--error)"],
    ];
    for (const [utilization, tone] of cases) {
      const { container, unmount } = renderWithProviders(
        <CashCard
          register={makeRegister({ limit_utilization: utilization })}
        />,
      );
      const bar = container.querySelector(".progress__bar");
      expect(bar).not.toBeNull();
      expect(bar?.getAttribute("style")).toContain(tone);
      unmount();
    }
  });
});
